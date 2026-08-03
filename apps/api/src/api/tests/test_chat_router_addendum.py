from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from api.chat_router.messages.stages import resolve_addendum
from api.services.message_classifier import MessageType


class _StubMessageClassifier:
    def __init__(self, message_type: MessageType = MessageType.CHAT) -> None:
        self._message_type = message_type

    def classify_message(self, *_args, **_kwargs):
        return SimpleNamespace(message_type=self._message_type)


@pytest.mark.asyncio
async def test_resolve_addendum_layers_research_guidance_for_live_questions():
    with (
        patch(
            "api.chat_router.messages._get_message_classifier",
            return_value=(_StubMessageClassifier(), MessageType),
        ),
        patch(
            "api.services.preference_learner.preference_learner.get_length_pref",
            new=AsyncMock(return_value="medium"),
        ),
    ):
        addendum = await resolve_addendum(
            mode=None,
            new_category="coding",
            intent_meta={"label": "research"},
            user_id="user_123",
            sanitized_message="What is the latest on AI policy?",
        )

    assert "You are helping with research or analysis." in addendum
    assert "web_search or lightweight_research" in addendum


@pytest.mark.asyncio
async def test_resolve_addendum_layers_finance_guidance_for_live_market_questions():
    with (
        patch(
            "api.chat_router.messages._get_message_classifier",
            return_value=(_StubMessageClassifier(), MessageType),
        ),
        patch(
            "api.services.preference_learner.preference_learner.get_length_pref",
            new=AsyncMock(return_value="medium"),
        ),
    ):
        addendum = await resolve_addendum(
            mode=None,
            new_category="coding",
            intent_meta={"label": "finance"},
            user_id="user_123",
            sanitized_message="What is the latest on AAPL and NVDA?",
        )

    assert "You are helping with personal finance." in addendum
    assert "prices, history, financials" in addendum
    assert "web_search, lightweight_research, or news tools" in addendum
