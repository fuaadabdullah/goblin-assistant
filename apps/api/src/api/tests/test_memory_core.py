from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.services.memory_core import (
    MemoryKind,
    MemoryLifecycleState,
    MemoryRecord,
    MemorySensitivity,
    _compute_memory_confidence,
    _compute_memory_importance,
    _compute_salience,
    _derive_explicitness_score,
    _derive_memory_state,
    _merge_memory_state,
    _normalize_scope,
    memory_core_service,
)
from api.storage.vector_models import MemoryFactModel


def test_compute_salience_boosts_active_context():
    baseline = _compute_salience(
        created_at=datetime.now(timezone.utc),
        confidence=0.7,
        repetition_count=1,
        active_context=False,
        user_importance=0.5,
        memory_type=MemoryKind.FACT,
    )
    boosted = _compute_salience(
        created_at=datetime.now(timezone.utc),
        confidence=0.7,
        repetition_count=1,
        active_context=True,
        user_importance=0.5,
        memory_type=MemoryKind.FACT,
    )

    assert boosted > baseline


@pytest.mark.asyncio
async def test_ingest_text_redacts_sensitive_input(monkeypatch):
    captured = {}

    async def fake_upsert(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id="mem-1")

    monkeypatch.setattr(
        memory_core_service, "_upsert_memory_record", AsyncMock(side_effect=fake_upsert)
    )

    record = await memory_core_service.ingest_text(
        user_id="user-123",
        text="My password is secret123 and email is user@example.com",
        source_kind="chat",
        source_id="msg-1",
        metadata={"conversation_id": "conv-1"},
        confidence=0.9,
    )

    assert record is not None
    assert "secret123" not in captured["text"]
    assert "[REDACTED" in captured["text"]
    assert captured["source_kind"] == "chat"
    assert captured["memory_type"] in {MemoryKind.FACT, MemoryKind.PREFERENCE}


def test_memory_sensitivity_enum_values_are_stable():
    assert MemorySensitivity.HIGH.value == "high"
    assert MemoryKind.PREFERENCE.value == "preference"


def test_memory_fact_model_has_lifecycle_column():
    cols = {c.name for c in MemoryFactModel.__table__.columns}
    assert "memory_state" in cols


def test_memory_record_to_dict_exposes_canonical_contract():
    record = MemoryRecord(
        id="mem-1",
        user_id="user-123",
        content="User prefers concise technical explanations.",
        memory_type=MemoryKind.PREFERENCE,
        category="preference",
        source_kind="conversation",
        source_id="conv-456",
        confidence=0.94,
        importance=0.82,
        confidence_band="strong_stable_memory",
        confidence_reason="user-authored and repeated",
        importance_band="high",
        importance_reason="task relevant",
        salience_score=0.82,
        sensitivity_level=MemorySensitivity.LOW,
        retention_days=365,
        created_at=datetime(2026, 6, 11, 18, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 11, 18, 0, tzinfo=timezone.utc),
        expires_at=None,
        last_accessed_at=datetime(2026, 6, 11, 18, 3, tzinfo=timezone.utc),
        confirmation_count=2,
        is_archived=False,
        embedding_id="emb-123",
        related_memory_ids=["mem-0"],
        entity_refs=[{"type": "user", "value": "user"}],
        metadata={
            "summary": "Prefers concise technical explanations",
            "tags": ["preference", "style"],
            "conversation_id": "conv-456",
            "message_id": "msg-789",
        },
    )

    payload = record.to_dict()

    assert payload["type"] == "preference"
    assert payload["scope"] == "global"
    assert payload["content"] == "User prefers concise technical explanations."
    assert payload["summary"] == "Prefers concise technical explanations"
    assert payload["source"] == "conversation"
    assert payload["source_ref"] == {"conversation_id": "conv-456", "message_id": "msg-789"}
    assert payload["importance"] == 0.82
    assert payload["importance_band"] == "high"
    assert payload["confidence_band"] in {
        "strong_stable_memory",
        "likely_true_usable",
        "weak_needs_verification",
        "do_not_use_by_default",
    }
    assert 0.0 <= payload["recency_score"] <= 1.0
    assert payload["sensitivity"] == "low"
    assert payload["status"] == "active"
    assert payload["tags"] == ["preference", "style", "conversation"]
    assert payload["entities"] == ["user"]
    assert payload["embedding_id"] == "emb-123"
    assert payload["memory_type"] == "preference"
    assert payload["source_kind"] == "conversation"
    assert payload["salience_score"] == 0.82
    assert payload["entity_refs"] == [{"type": "user", "value": "user"}]
    assert payload["state"] == "active"
    assert payload["memory_state"] == "active"
    assert payload["status"] == "active"
    assert payload["authored"] is False
    assert payload["inferred"] is False
    assert payload["direct_correction"] is False
    assert payload["contradiction"] is False
    assert payload["later_contradicted"] is False
    assert payload["repetition_count"] == 1
    assert payload["explicitness_score"] >= 0.0


def test_confidence_scoring_respects_provenance_signals():
    high = _compute_memory_confidence(
        base_confidence=0.8,
        explicitness=0.95,
        repetition_count=3,
        authored=True,
        inferred=False,
        direct_correction=True,
        contradiction=False,
        later_contradicted=False,
        conflict_penalty=0.0,
    )
    low = _compute_memory_confidence(
        base_confidence=0.8,
        explicitness=0.4,
        repetition_count=1,
        authored=False,
        inferred=True,
        direct_correction=False,
        contradiction=True,
        later_contradicted=True,
        conflict_penalty=0.6,
    )

    assert high > low
    assert high >= 0.7
    assert low < 0.7


def test_importance_scoring_prefers_task_relevant_repeated_memory():
    project_memory = _compute_memory_importance(
        repetition_count=4,
        use_frequency=0.9,
        task_relevance=0.95,
        explicit_emphasis=0.8,
        dependency_level=0.9,
        future_behavior_impact=0.95,
        memory_type=MemoryKind.PROJECT_STATE,
        scope="project",
    )
    random_memory = _compute_memory_importance(
        repetition_count=1,
        use_frequency=0.1,
        task_relevance=0.1,
        explicit_emphasis=0.1,
        dependency_level=0.0,
        future_behavior_impact=0.1,
        memory_type=MemoryKind.FACT,
        scope="global",
    )

    assert project_memory > random_memory
    assert project_memory >= 0.7
    assert random_memory < 0.5


def test_scope_derivation_prefers_project_conversation_and_tool():
    assert _normalize_scope({"project_id": "p1"}, "memory") == "project"
    assert _normalize_scope({"conversation_id": "c1"}, "memory") == "conversation"
    assert _normalize_scope({"tool_name": "search"}, "tool_result") == "tool"
    assert _normalize_scope({}, "memory") == "global"


def test_explicitness_score_prefers_direct_language():
    assert _derive_explicitness_score("I prefer concise answers", {}) > _derive_explicitness_score(
        "The user mentioned concise answers once", {}
    )


def test_memory_state_resolution_prefers_direct_correction():
    state = _derive_memory_state(
        metadata={"direct_correction": True, "memory_state": None},
        confidence=0.75,
        repetition_count=1,
        authored=True,
        inferred=False,
        direct_correction=True,
        contradiction=False,
        later_contradicted=False,
        importance=0.8,
        source_kind="conversation",
        explicit_kind="preference",
    )
    assert state == MemoryLifecycleState.VERIFIED


def test_memory_state_resolution_demotes_contradictions():
    state = _derive_memory_state(
        metadata={"contradiction": True},
        confidence=0.6,
        repetition_count=2,
        authored=True,
        inferred=False,
        direct_correction=False,
        contradiction=True,
        later_contradicted=False,
        importance=0.5,
        source_kind="summary",
        explicit_kind="fact",
    )
    assert state == MemoryLifecycleState.DEPRECATED


def test_memory_state_merge_preserves_terminal_states():
    assert (
        _merge_memory_state("active", MemoryLifecycleState.VERIFIED)
        == MemoryLifecycleState.VERIFIED
    )
    assert (
        _merge_memory_state("archived", MemoryLifecycleState.ACTIVE)
        == MemoryLifecycleState.ARCHIVED
    )


@pytest.mark.asyncio
async def test_retrieve_memory_context_returns_canonical_items(monkeypatch):
    fake_item = {
        "id": "mem-2",
        "fact_text": "User wants project decisions stored.",
        "category": "project",
        "memory_type": "project_state",
        "source_kind": "conversation",
        "source_id": "conv-789",
        "salience_score": 0.77,
        "confidence": 0.91,
        "sensitivity_level": "low",
        "retention_days": 90,
        "expires_at": None,
        "last_accessed_at": datetime(2026, 6, 11, 18, 3, tzinfo=timezone.utc),
        "confirmation_count": 1,
        "is_archived": False,
        "related_memory_ids": [],
        "entity_refs": [{"type": "project", "value": "goblin-assistant"}],
        "metadata": {
            "conversation_id": "conv-789",
            "tags": ["project", "decision"],
        },
        "created_at": datetime(2026, 6, 11, 18, 0, tzinfo=timezone.utc),
        "score": 0.88,
        "source_type": "memory",
    }

    monkeypatch.setattr(
        "api.services.retrieval_service.retrieval_service.retrieve_memory_facts",
        AsyncMock(return_value=[fake_item]),
    )
    monkeypatch.setattr(
        "api.services.memory_reranker.memory_reranker.rerank",
        lambda items, query, top_k=None: items,
    )

    results = await memory_core_service.retrieve_memory_context(
        user_id="user-123",
        query="project decisions",
        limit=1,
    )

    assert len(results) == 1
    item = results[0]
    assert item["type"] == "project_state"
    assert item["scope"] == "conversation"
    assert item["source"] == "conversation"
    assert item["source_ref"] == {"conversation_id": "conv-789"}
    assert item["importance"] == 0.77
    assert item["confidence"] == 0.91
    assert item["status"] == "active"
    assert item["tags"] == ["project", "decision", "project_state", "conversation"]
    assert item["entities"] == ["goblin-assistant"]
    assert item["memory_type"] == "project_state"
    assert item["fact_text"] == "User wants project decisions stored."
