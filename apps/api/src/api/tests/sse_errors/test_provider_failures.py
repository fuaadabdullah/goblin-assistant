"""Provider Failures SSE tests."""

import asyncio
from unittest.mock import AsyncMock, patch

from api.chat_router import generate_chat_stream

from .conftest import _content_events, _error_events, parse_sse_event


async def test_provider_timeout_returns_recoverable_error(
    authenticated_user,
    test_conversation,
):
    with (
        patch(
            "api.chat_router._require_owned_conversation",
            return_value=test_conversation,
        ),
        patch(
            "api.chat_router.InputSanitizer.sanitize_chat_message",
            return_value=("test", None),
        ),
        patch(
            "api.chat_router.conversation_store.add_message_to_conversation",
            new_callable=AsyncMock,
        ),
        patch(
            "api.chat_router.invoke_provider",
            side_effect=asyncio.TimeoutError(),
        ),
    ):
        events = []
        async for event in generate_chat_stream(
            message="test",
            conversation_id="test-conv-id",
            current_user=authenticated_user,
            provider="test-provider",
        ):
            events.append(event)

    error_events = _error_events(events)

    assert any(
        event.get("code") == "provider-timeout" and event.get("is_recoverable") is True
        for event in error_events
    )


async def test_fallback_timeout_returns_error_event(
    authenticated_user,
    test_conversation,
):
    with (
        patch(
            "api.chat_router._require_owned_conversation",
            return_value=test_conversation,
        ),
        patch(
            "api.chat_router.InputSanitizer.sanitize_chat_message",
            return_value=("test", None),
        ),
        patch(
            "api.chat_router.conversation_store.add_message_to_conversation",
            new_callable=AsyncMock,
        ),
        patch(
            "api.chat_router.conversation_store.get_conversation",
            return_value=test_conversation,
        ),
        patch(
            "api.chat_router.invoke_provider",
            side_effect=[
                {"ok": False, "error": "streaming-error"},
                asyncio.TimeoutError(),
            ],
        ),
    ):
        events = []
        async for event in generate_chat_stream(
            message="test",
            conversation_id="test-conv-id",
            current_user=authenticated_user,
        ):
            events.append(event)

    error_events = _error_events(events)

    assert any(event.get("code") == "provider-timeout" for event in error_events)
    assert any(event.get("is_recoverable") is True for event in error_events)


async def test_provider_error_fallback_to_nonstreaming(
    authenticated_user,
    test_conversation,
):
    fallback_response = {
        "ok": True,
        "result": {"text": "Fallback response"},
        "provider": "test-provider",
        "model": "test-model",
    }

    with (
        patch(
            "api.chat_router._require_owned_conversation",
            return_value=test_conversation,
        ),
        patch(
            "api.chat_router.InputSanitizer.sanitize_chat_message",
            return_value=("test", None),
        ),
        patch(
            "api.chat_router.conversation_store.add_message_to_conversation",
            new_callable=AsyncMock,
        ),
        patch(
            "api.chat_router.conversation_store.get_conversation",
            return_value=test_conversation,
        ),
        patch("api.chat_router.invoke_provider") as mock_invoke,
    ):
        mock_invoke.side_effect = [
            {"ok": False, "error": "streaming-error"},
            fallback_response,
        ]

        events = []
        async for event in generate_chat_stream(
            message="test",
            conversation_id="test-conv-id",
            current_user=authenticated_user,
        ):
            events.append(event)

    content_events = _content_events(events)

    assert any(event.get("content") == "Fallback response" for event in content_events)
    assert parse_sse_event(events[-1]).get("done") is True


async def test_provider_error_fallback_returns_provider_error_event(
    authenticated_user,
    test_conversation,
):
    with (
        patch(
            "api.chat_router._require_owned_conversation",
            return_value=test_conversation,
        ),
        patch(
            "api.chat_router.InputSanitizer.sanitize_chat_message",
            return_value=("test", None),
        ),
        patch(
            "api.chat_router.conversation_store.add_message_to_conversation",
            new_callable=AsyncMock,
        ),
        patch(
            "api.chat_router.conversation_store.get_conversation",
            return_value=test_conversation,
        ),
        patch(
            "api.chat_router.invoke_provider",
            side_effect=[
                {"ok": False, "error": "streaming-error"},
                {"ok": False, "error": "fallback-failed"},
            ],
        ),
    ):
        events = []
        async for event in generate_chat_stream(
            message="test",
            conversation_id="test-conv-id",
            current_user=authenticated_user,
        ):
            events.append(event)

    error_events = _error_events(events)

    assert any(event.get("code") == "provider-error" for event in error_events)
    assert any(
        event.get("details", {}).get("provider_error") == "streaming-error"
        for event in error_events
    )


async def test_provider_error_fallback_exception_returns_error_event(
    authenticated_user,
    test_conversation,
):
    with (
        patch(
            "api.chat_router._require_owned_conversation",
            return_value=test_conversation,
        ),
        patch(
            "api.chat_router.InputSanitizer.sanitize_chat_message",
            return_value=("test", None),
        ),
        patch(
            "api.chat_router.conversation_store.add_message_to_conversation",
            new_callable=AsyncMock,
        ),
        patch(
            "api.chat_router.conversation_store.get_conversation",
            return_value=test_conversation,
        ),
        patch(
            "api.chat_router.invoke_provider",
            side_effect=[
                {"ok": False, "error": "streaming-error"},
                RuntimeError("fallback failed"),
            ],
        ),
    ):
        events = []
        async for event in generate_chat_stream(
            message="test",
            conversation_id="test-conv-id",
            current_user=authenticated_user,
        ):
            events.append(event)

    error_events = _error_events(events)

    assert any(event.get("code") == "provider-error" for event in error_events)
    assert any(
        event.get("message") == "Provider unavailable. Your message was saved."
        for event in error_events
    )
