from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.services.goblin_identity import (
    goblin_aliases,
    is_known_goblin_identifier,
    message_matches_goblin,
    resolve_goblin_id,
)
from api.services.goblin_query_service import ConversationGoblinHistoryRepository
from api.storage.conversations_pkg.in_memory import InMemoryConversationStore
from api.storage.conversations_pkg.models import Conversation, ConversationMessage


def test_resolve_goblin_id_prefers_explicit_goblin_metadata():
    assert (
        resolve_goblin_id(
            metadata={"goblin_id": "finance", "provider": "openai"},
            department="coding",
            fallback="general",
        )
        == "finance"
    )


def test_resolve_goblin_id_ignores_provider_fallbacks():
    assert (
        resolve_goblin_id(
            metadata={"provider": "openai"},
            department="coding",
            fallback="general",
        )
        == "coding"
    )


def test_goblin_aliases_include_legacy_department_and_provider_ids():
    aliases = goblin_aliases("finance")

    assert "finance" in aliases
    assert "reasoning" in aliases
    assert "openai" in aliases


def test_known_goblin_identifiers_accept_legacy_aliases():
    assert is_known_goblin_identifier("finance") is True
    assert is_known_goblin_identifier("reasoning") is True
    assert is_known_goblin_identifier("openai") is True
    assert is_known_goblin_identifier("not-a-goblin") is False


def test_message_matches_goblin_accepts_canonical_and_legacy_aliases():
    assert message_matches_goblin({"goblin_id": "openai"}, "finance") is True
    assert message_matches_goblin({"department": "reasoning"}, "finance") is True
    assert message_matches_goblin({"goblin_id": "finance"}, "finance") is True
    assert message_matches_goblin({"goblin_id": "totally-unknown-provider"}, "coding") is False


def test_message_matches_goblin_checks_all_legacy_metadata_fields():
    assert (
        message_matches_goblin(
            {"goblin_id": "general", "goblin": "openai", "provider": "openai"},
            "finance",
        )
        is True
    )


@pytest.mark.asyncio
async def test_history_repository_matches_legacy_provider_metadata(monkeypatch):
    assistant = SimpleNamespace(
        role="assistant",
        content="legacy response",
        metadata={"provider": "openai", "status": "completed"},
        message_id="msg-1",
        timestamp=datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc),
    )
    user = SimpleNamespace(
        role="user",
        content="legacy prompt",
        metadata={},
        message_id="msg-0",
        timestamp=datetime(2026, 8, 18, 11, 59, tzinfo=timezone.utc),
    )
    conversation = SimpleNamespace(
        conversation_id="conv-1",
        user_id="user-1",
        messages=[user, assistant],
    )

    fake_store = SimpleNamespace(
        list_conversations=AsyncMock(return_value=[conversation]),
    )
    monkeypatch.setattr("api.storage.conversation_store", fake_store)

    repository = ConversationGoblinHistoryRepository()
    entries = await repository.list_history(user_id="user-1", goblin_id="finance", scan_limit=10)

    assert len(entries) == 1
    assert entries[0].goblin_id == "finance"
    assert entries[0].task == "legacy prompt"
    assert entries[0].response == "legacy response"


@pytest.mark.asyncio
async def test_in_memory_stats_match_provider_only_legacy_rows():
    store = InMemoryConversationStore()
    conversation = Conversation(
        conversation_id="conv-2",
        user_id="user-1",
        messages=[
            ConversationMessage(
                role="user",
                content="legacy prompt",
                message_id="msg-0",
                timestamp=datetime(2026, 8, 18, 11, 59, tzinfo=timezone.utc),
            ),
            ConversationMessage(
                role="assistant",
                content="legacy response",
                message_id="msg-1",
                metadata={"provider": "openai", "status": "completed", "cost_usd": 0.125},
                timestamp=datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc),
            ),
        ],
    )
    await store.save_conversation(conversation)

    stats = await store.get_goblin_stats(
        user_id="user-1",
        goblin_id="finance",
        started_at=datetime(2026, 8, 18, 11, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 8, 18, 13, 0, tzinfo=timezone.utc),
    )

    assert stats["total_tasks"] == 1
    assert stats["completed_tasks"] == 1
    assert stats["failed_tasks"] == 0
    assert stats["success_rate"] == 1.0
    assert stats["total_cost"] == 0.125


@pytest.mark.asyncio
async def test_in_memory_stats_match_mixed_legacy_rows():
    store = InMemoryConversationStore()
    conversation = Conversation(
        conversation_id="conv-3",
        user_id="user-1",
        messages=[
            ConversationMessage(
                role="user",
                content="mixed prompt",
                message_id="msg-0",
                timestamp=datetime(2026, 8, 18, 11, 59, tzinfo=timezone.utc),
            ),
            ConversationMessage(
                role="assistant",
                content="mixed response",
                message_id="msg-1",
                metadata={
                    "goblin_id": "general",
                    "goblin": "openai",
                    "provider": "openai",
                    "status": "completed",
                    "cost_usd": 0.25,
                },
                timestamp=datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc),
            ),
        ],
    )
    await store.save_conversation(conversation)

    stats = await store.get_goblin_stats(
        user_id="user-1",
        goblin_id="finance",
        started_at=datetime(2026, 8, 18, 11, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 8, 18, 13, 0, tzinfo=timezone.utc),
    )

    assert stats["total_tasks"] == 1
    assert stats["completed_tasks"] == 1
    assert stats["failed_tasks"] == 0
    assert stats["success_rate"] == 1.0
    assert stats["total_cost"] == 0.25
