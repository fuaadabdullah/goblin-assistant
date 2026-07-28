"""Tests for memory promotion ingest routing."""

from __future__ import annotations

from datetime import datetime
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.services.memory_promotion._service import MemoryPromotionService
from api.services.memory_promotion.models import PromotionCandidate


class _FakeDBContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_store_memory_fact_routes_through_memory_core(monkeypatch):
    module = import_module("api.services.memory_promotion._service")
    monkeypatch.setattr(
        module,
        "evaluate_content_quality",
        lambda content: 1.0,
    )
    monkeypatch.setattr(module, "evaluate_stability", lambda content: 1.0)

    service = MemoryPromotionService()
    service.retrieval_service = SimpleNamespace(
        retrieve_memory_facts=AsyncMock(
            return_value=[
                {
                    "conversation_id": "conv-a",
                    "created_at": datetime.utcnow(),
                },
                {
                    "conversation_id": "conv-b",
                    "created_at": datetime.utcnow(),
                },
            ]
        )
    )
    monkeypatch.setattr(
        module.observability_service,
        "log_memory_promotion_event",
        MagicMock(),
    )
    monkeypatch.setattr(module.event_emitter, "emit", AsyncMock())

    fake_record = SimpleNamespace(id="memory-123")
    memory_core_mock = AsyncMock()
    memory_core_mock.ingest_memory_fact = AsyncMock(return_value=fake_record)
    monkeypatch.setattr("api.services.memory_core.memory_core_service", memory_core_mock)

    candidate = PromotionCandidate(
        content="I prefer concise technical explanations.",
        category="preference",
        source_conversation="conv-123",
        source_type="summary",
        confidence=0.95,
        metadata={"user_id": "user-123"},
        created_at=datetime.utcnow(),
    )

    result = await service.evaluate_promotion_candidate(candidate)

    assert result.promoted is True
    assert result.memory_fact_id == "memory-123"
    memory_core_mock.ingest_memory_fact.assert_awaited_once()
    kwargs = memory_core_mock.ingest_memory_fact.await_args.kwargs
    assert kwargs["user_id"] == "user-123"
    assert kwargs["fact_text"] == candidate.content
    assert kwargs["category"] == candidate.category
    assert kwargs["metadata"]["source_conversation"] == "conv-123"


@pytest.mark.asyncio
async def test_similar_memory_lookup_uses_user_scope(monkeypatch):
    embedding_service = AsyncMock()
    embedding_service.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])

    module = import_module("api.services.memory_promotion._service")
    monkeypatch.setattr(module, "EmbeddingService", lambda: embedding_service)

    service = MemoryPromotionService()
    service.retrieval_service = SimpleNamespace(retrieve_memory_facts=AsyncMock(return_value=[]))

    find_similar = getattr(service, "_find_similar_memory_facts")
    await find_similar(
        "remember this",
        "preference",
        user_id="user-123",
    )

    service.retrieval_service.retrieve_memory_facts.assert_awaited_once_with(
        user_id="user-123",
        query="remember this",
        categories=["preference"],
        k=10,
    )


@pytest.mark.asyncio
async def test_build_ingest_metadata_keeps_both_across_scopes():
    service = MemoryPromotionService()
    service.retrieval_service = SimpleNamespace(
        retrieve_memory_facts=AsyncMock(
            return_value=[
                {
                    "id": "mem-global",
                    "content": "User prefers concise answers.",
                    "scope": "global",
                    "confidence": 0.95,
                    "metadata": {"scope": "global"},
                },
                {
                    "id": "mem-project",
                    "content": "User wants architecture explanations in more detail.",
                    "scope": "project",
                    "confidence": 0.88,
                    "metadata": {"scope": "project"},
                },
            ]
        )
    )

    candidate = PromotionCandidate(
        content="User wants more detail for architecture explanations.",
        category="preference",
        source_conversation="conv-123",
        source_type="summary",
        confidence=0.92,
        metadata={"user_id": "user-123", "conversation_id": "conv-123"},
        created_at=datetime.utcnow(),
    )

    ingest_metadata = await service._build_ingest_metadata(candidate)

    assert ingest_metadata["keep_both"] is True
    assert ingest_metadata["conflicting_memory_ids"] == []
    assert ingest_metadata["conflict_scopes"] == ["global", "project"]
    assert ingest_metadata["conflict_resolution"] == "keep_both"
