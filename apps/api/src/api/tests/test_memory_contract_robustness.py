"""Deterministic boundary tests for the memory contract."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from api.services.memory_contract import (
    DEFAULT_MEMORY_STATE,
    DEFAULT_SCOPE,
    MemoryContractInput,
    build_memory_contract_payload,
    canonicalize_memory_item,
    get_deprecated_memory_contract_field_counts,
    reset_deprecated_memory_contract_field_counts,
)


def _build_payload(**overrides):
    payload = {
        "id": "mem-1",
        "content": "Test fact",
    }
    payload.update(overrides)
    return build_memory_contract_payload(**payload)


def test_normalized_input_coerces_and_freezes_legacy_fields():
    normalized = MemoryContractInput.from_legacy_kwargs(
        id=123,
        content="  Hello\n   world  ",
        user_id=456,
        metadata={"summary": "  Compact  summary ", "conversation_id": "conv-1"},
        source_kind="conversation",
        source_id="conv-1",
        authored=True,
    )

    assert normalized.id == "123"
    assert normalized.content == "Hello world"
    assert normalized.user_id == "456"
    assert normalized.summary == "Compact summary"
    assert normalized.scope == "conversation"
    assert normalized.source_ref == {"conversation_id": "conv-1"}
    assert normalized.recency_score == 0.5


def test_versioned_contract_emits_stable_schema_version():
    payload = _build_payload()

    assert payload["schema_version"] == "1.0"
    assert "contract_version" not in payload
    assert canonicalize_memory_item({"id": "mem-2", "content": "Test"})["schema_version"] == "1.0"


def test_contract_version_is_not_emitted_by_v1_payload():
    payload = _build_payload()

    assert "contract_version" not in payload
    assert payload.get("contract_version") is None


def test_deprecated_aliases_are_tracked_and_emitted():
    reset_deprecated_memory_contract_field_counts()

    payload = _build_payload(
        memory_type="fact",
        salience_score=0.7,
        sensitivity_level="low",
        memory_state="active",
    )

    assert payload["deprecated_fields"] == [
        "memory_type",
        "salience_score",
        "sensitivity_level",
        "memory_state",
    ]
    counts = get_deprecated_memory_contract_field_counts()
    assert counts["memory_type"] == 1
    assert counts["salience_score"] == 1
    assert counts["sensitivity_level"] == 1
    assert counts["memory_state"] == 1


def test_legacy_item_aliases_are_tracked():
    reset_deprecated_memory_contract_field_counts()

    payload = canonicalize_memory_item(
        {
            "id": "mem-3",
            "fact_text": "User prefers concise answers.",
            "memory_type": "preference",
            "salience_score": 0.6,
            "sensitivity_level": "low",
            "memory_state": "active",
        }
    )

    assert payload["memory_id"] == "mem-3"
    assert payload["deprecated_fields"] == [
        "fact_text",
        "memory_type",
        "salience_score",
        "sensitivity_level",
        "memory_state",
    ]
    counts = get_deprecated_memory_contract_field_counts()
    assert counts["fact_text"] == 1


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"scope": "user", "metadata": {"project_id": "p1"}}, "user"),
        (
            {"metadata": {"project_id": "p1", "conversation_id": "c1", "tool_name": "search"}},
            "project",
        ),
        ({"metadata": {"conversation_id": "c1", "tool_name": "search"}}, "conversation"),
        ({"metadata": {"tool_name": "search"}}, "tool"),
        ({}, DEFAULT_SCOPE),
    ],
)
def test_scope_precedence_is_explicit_and_bounded(kwargs, expected):
    payload = _build_payload(**kwargs)

    assert payload["scope"] == expected


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"metadata": {"summary": "  Explicit summary  "}}, "Explicit summary"),
        ({"metadata": {"short_summary": "  Short summary  "}}, "Short summary"),
        ({"content": "One line fact"}, "One line fact"),
        ({"content": "x" * 200}, "x" * 157 + "..."),
    ],
)
def test_summary_is_derived_from_explicit_or_content_boundary(kwargs, expected):
    payload = _build_payload(**kwargs)

    assert payload["summary"] == expected


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (
            {
                "source_kind": "conversation",
                "source_id": "conv-1",
                "metadata": {},
            },
            {"conversation_id": "conv-1"},
        ),
        (
            {
                "source_kind": "message",
                "source_id": "msg-1",
                "metadata": {},
            },
            {"message_id": "msg-1"},
        ),
        (
            {
                "source_kind": "tool",
                "source_id": "tool-1",
                "metadata": {"tool_name": "search"},
            },
            {"tool_name": "search"},
        ),
        (
            {
                "source_kind": "memory",
                "source_id": "raw-1",
                "metadata": {},
            },
            {"source_id": "raw-1"},
        ),
    ],
)
def test_source_ref_uses_source_specific_boundaries(kwargs, expected):
    payload = _build_payload(**kwargs)

    assert payload["source_ref"] == expected


@pytest.mark.parametrize(
    ("kwargs", "expected_state", "expected_status", "expected_archived"),
    [
        ({"state": "verified"}, "verified", "verified", False),
        ({"metadata": {"deleted": True}}, "deleted", "deleted", True),
        ({"is_archived": True}, "archived", "archived", True),
        (
            {"expires_at": datetime(2000, 1, 1, tzinfo=timezone.utc)},
            "archived",
            "archived",
            True,
        ),
    ],
)
def test_state_status_and_archived_flags_follow_terminal_rules(
    kwargs,
    expected_state,
    expected_status,
    expected_archived,
):
    payload = _build_payload(**kwargs)

    assert payload["state"] == expected_state
    assert payload["status"] == expected_status
    assert payload["is_archived"] is expected_archived


def test_recency_score_uses_expected_boundary_values():
    cold = _build_payload(
        created_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
        last_accessed_at=None,
    )
    fresh = _build_payload(
        created_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
        last_accessed_at=datetime.now(timezone.utc),
    )

    assert cold["recency_score"] < 0.1
    assert 0.99 <= fresh["recency_score"] <= 1.0


def test_tags_and_entities_are_deduped_in_stable_order():
    payload = _build_payload(
        category="preference",
        memory_type="preference",
        source_kind="conversation",
        metadata={
            "tags": ["alpha", "preference", "alpha"],
            "entities": ["alice", "alice"],
        },
        entity_refs=[
            {"name": "bob"},
            {"id": "carol"},
            {"value": "alice"},
            "dave",
        ],
    )

    assert payload["tags"] == ["alpha", "preference", "conversation"]
    assert payload["entities"] == ["alice", "bob", "carol", "dave"]


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [
        (0.90, "strong_stable_memory"),
        (0.70, "likely_true_usable"),
        (0.40, "weak_needs_verification"),
        (0.39, "do_not_use_by_default"),
    ],
)
def test_confidence_band_thresholds_are_pinned(confidence, expected):
    payload = _build_payload(confidence=confidence)

    assert payload["confidence_band"] == expected


@pytest.mark.parametrize(
    ("importance", "expected"),
    [
        (0.80, "high"),
        (0.55, "medium"),
        (0.54, "low"),
    ],
)
def test_importance_band_thresholds_are_pinned(importance, expected):
    payload = _build_payload(importance=importance)

    assert payload["importance_band"] == expected


def test_memory_type_source_kind_and_sensitivity_precedence():
    payload = _build_payload(
        memory_type="decision",
        category="preference",
        source_kind="chat",
        metadata={"memory_type": "fact", "source_kind": "tool", "sensitivity_level": "high"},
        sensitivity_level="medium",
    )

    assert payload["type"] == "decision"
    assert payload["memory_type"] == "decision"
    assert payload["source_kind"] == "chat"
    assert payload["source"] == "chat"
    assert payload["sensitivity"] == "medium"
    assert payload["sensitivity_level"] == "medium"


def test_scalar_defaults_and_related_ids_are_normalized():
    payload = _build_payload(
        authored=True,
        related_memory_ids=["mem-2", "mem-2", 3],
        confirmation_count=None,
        repetition_count=None,
    )

    assert payload["confirmation_count"] == 0
    assert payload["repetition_count"] == 1
    assert payload["explicitness_score"] == 0.75
    assert payload["related_memory_ids"] == ["mem-2", "3"]
    assert payload["schema_version"] == "1.0"
    assert "contract_version" not in payload
    assert payload["state"] == DEFAULT_MEMORY_STATE
    assert payload["status"] == DEFAULT_MEMORY_STATE


def test_canonicalize_memory_item_returns_the_same_versioned_shape():
    item = {
        "id": "mem-3",
        "content": "Memory row",
        "fact_text": "Memory row",
        "metadata": {"summary": "Row summary", "conversation_id": "conv-9"},
    }

    payload = canonicalize_memory_item(item, user_id="user-9")

    assert payload["schema_version"] == "1.0"
    assert "contract_version" not in payload
    assert payload["summary"] == "Row summary"
    assert payload["source_ref"] == {"conversation_id": "conv-9"}
