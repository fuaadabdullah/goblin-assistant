from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from api.assistant_tools.skills.memory_recall import _handle_memory_recall


@pytest.mark.asyncio
async def test_memory_recall_success_normalizes_payload():
    rows = [
        {
            "id": "mf_1",
            "fact_text": "User prefers concise answers",
            "category": "preference",
            "score": 0.91,
            "created_at": datetime(2026, 5, 30, tzinfo=timezone.utc),
        }
    ]

    with patch(
        "api.assistant_tools.skills.memory_recall.RetrievalService.retrieve_memory_facts",
        new=AsyncMock(return_value=rows),
    ):
        result = await _handle_memory_recall(
            query="How should I respond?",
            user_id="user_123",
            conversation_id="conv_1",
            limit=5,
        )

    assert result["count"] == 1
    assert result["user_id"] == "user_123"
    assert result["conversation_id"] == "conv_1"
    assert result["memory_facts"][0]["content"] == "User prefers concise answers"
    assert result["memory_facts"][0]["created_at"] == "2026-05-30T00:00:00+00:00"


@pytest.mark.asyncio
async def test_memory_recall_empty_results():
    with patch(
        "api.assistant_tools.skills.memory_recall.RetrievalService.retrieve_memory_facts",
        new=AsyncMock(return_value=[]),
    ):
        result = await _handle_memory_recall(
            query="No facts",
            user_id="user_123",
            conversation_id=None,
            limit=3,
        )

    assert result["count"] == 0
    assert result["memory_facts"] == []


@pytest.mark.asyncio
async def test_memory_recall_requires_user_scope():
    result = await _handle_memory_recall(query="hello", user_id="", conversation_id=None, limit=5)
    assert result["error"] == "user_id is required"
