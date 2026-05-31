"""Tests for memory promotion embedding storage."""

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
async def test_store_memory_fact_persists_embedding(monkeypatch):
    embedding_service = AsyncMock()
    embedding_service.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])

    module = import_module("api.services.memory_promotion._service")
    monkeypatch.setattr(module, "EmbeddingService", lambda: embedding_service)
    monkeypatch.setattr(
        module,
        "evaluate_content_quality",
        lambda content: 1.0,
    )
    monkeypatch.setattr(module, "evaluate_stability", lambda content: 1.0)

    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    monkeypatch.setattr(
        module,
        "get_db_context",
        lambda: _FakeDBContext(session),
    )

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
    assert result.memory_fact_id is not None
    embedding_service.embed_text.assert_awaited_once_with(candidate.content)
    session.commit.assert_awaited_once()

    stored_model = session.add.call_args.args[0]
    assert stored_model.user_id == "user-123"
    assert stored_model.fact_text == candidate.content
    assert stored_model.fact_embedding == [0.1, 0.2, 0.3]
    assert stored_model.metadata_["source_conversation"] == "conv-123"


@pytest.mark.asyncio
async def test_similar_memory_lookup_uses_user_scope(monkeypatch):
    embedding_service = AsyncMock()
    embedding_service.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])

    module = import_module("api.services.memory_promotion._service")
    monkeypatch.setattr(module, "EmbeddingService", lambda: embedding_service)

    service = MemoryPromotionService()
    service.retrieval_service = SimpleNamespace(
        retrieve_memory_facts=AsyncMock(return_value=[])
    )

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
