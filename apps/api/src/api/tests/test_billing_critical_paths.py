from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from api.chat_router.messages.stages import check_usage_quota
from api.chat_router.messages.usage_tracker import record_usage_event


@pytest.mark.asyncio
async def test_chat_quota_gate_blocks_before_provider_dispatch():
    usage_store = MagicMock()
    usage_store.check_limits = AsyncMock(
        return_value={
            "allowed": False,
            "reason": "daily_cost_limit_exceeded",
            "usage": {"total_cost_usd": 12.34},
        }
    )

    with patch(
        "api.chat_router.messages.get_usage_event_store",
        new=AsyncMock(return_value=usage_store),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await check_usage_quota("user-1", "conversation-1")

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == {
        "message": "Daily usage limit exceeded",
        "reason": "daily_cost_limit_exceeded",
        "usage": {"total_cost_usd": 12.34},
    }
    usage_store.check_limits.assert_awaited_once_with("user-1")


@pytest.mark.asyncio
async def test_chat_quota_gate_degrades_open_when_usage_store_fails():
    usage_store = MagicMock()
    usage_store.check_limits = AsyncMock(side_effect=RuntimeError("usage store unavailable"))

    with patch(
        "api.chat_router.messages.get_usage_event_store",
        new=AsyncMock(return_value=usage_store),
    ):
        await check_usage_quota("user-1", "conversation-1")

    usage_store.check_limits.assert_awaited_once_with("user-1")


@pytest.mark.asyncio
async def test_chat_completion_usage_event_records_billable_provider_cost():
    usage_store = MagicMock()
    usage_store.save_event = AsyncMock(return_value="usage-1")

    with patch(
        "api.chat_router.messages.get_usage_event_store",
        new=AsyncMock(return_value=usage_store),
    ):
        await record_usage_event(
            user_id="user-1",
            conversation_id="conversation-1",
            message_id="message-1",
            provider="openai",
            model="gpt-4o-mini",
            usage={"prompt_tokens": 12, "completion_tokens": 8},
            cost_usd=0.0042,
            correlation_id="route-123",
            latency_ms=321.0,
        )

    usage_store.save_event.assert_awaited_once()
    event = usage_store.save_event.await_args.args[0]
    assert event["user_id"] == "user-1"
    assert event["conversation_id"] == "conversation-1"
    assert event["message_id"] == "message-1"
    assert event["provider"] == "openai"
    assert event["model"] == "gpt-4o-mini"
    assert event["prompt_tokens"] == 12
    assert event["completion_tokens"] == 8
    assert event["total_tokens"] == 20
    assert event["cost_usd"] == pytest.approx(0.0042)
    assert event["latency_ms"] == pytest.approx(321.0)
    assert event["metadata"] == {
        "source": "chat.send_message",
        "correlation_id": "route-123",
    }
