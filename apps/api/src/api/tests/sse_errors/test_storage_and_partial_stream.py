"""Storage And Partial Stream SSE tests."""

import asyncio
from unittest.mock import AsyncMock, patch

from api.chat_router import generate_chat_stream

from .conftest import _content_events, _error_events, parse_sse_event


async def test_user_message_stored_before_provider_call(
    authenticated_user,
    test_conversation,
):
    message_stored = False

    async def mock_add_message(**kwargs):
        nonlocal message_stored
        if kwargs.get("role") == "user":
            message_stored = True

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
            side_effect=mock_add_message,
        ),
        patch(
            "api.chat_router.invoke_provider",
            side_effect=asyncio.TimeoutError(),
        ),
    ):
        events = []
        async for event in generate_chat_stream(
            message="test message",
            conversation_id="test-conv-id",
            current_user=authenticated_user,
        ):
            events.append(event)

    assert message_stored
    assert any(event.get("code") == "provider-timeout" for event in _error_events(events))


async def test_stream_error_with_partial_response(
    authenticated_user,
    test_conversation,
):
    async def mock_stream_gen():
        yield {"text": "Hello "}
        yield {"text": "world"}
        raise RuntimeError("Stream interrupted")

    provider_response = {
        "ok": True,
        "stream": mock_stream_gen(),
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
        patch(
            "api.chat_router.invoke_provider",
            return_value=provider_response,
        ),
    ):
        events = []
        async for event in generate_chat_stream(
            message="test",
            conversation_id="test-conv-id",
            current_user=authenticated_user,
        ):
            events.append(event)

    content_events = _content_events(events)
    error_events = _error_events(events)

    assert any("Hello" in str(event.get("content", "")) for event in content_events)
    assert any("world" in str(event.get("content", "")) for event in content_events)
    assert any(
        event.get("code") == "stream-interrupted" and event.get("is_recoverable") is True
        for event in error_events
    )


async def test_chunk_processing_error_is_skipped_and_stream_completes(
    authenticated_user,
    test_conversation,
):
    class BadChunk:
        def __str__(self):
            raise RuntimeError("bad chunk")

    async def mock_stream_gen():
        yield {"text": "Hello "}
        yield BadChunk()
        yield {"text": "world"}

    provider_response = {
        "ok": True,
        "stream": mock_stream_gen(),
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
        patch(
            "api.chat_router.invoke_provider",
            return_value=provider_response,
        ),
    ):
        events = []
        async for event in generate_chat_stream(
            message="test",
            conversation_id="test-conv-id",
            current_user=authenticated_user,
        ):
            events.append(event)

    content_events = _content_events(events)
    final_event = parse_sse_event(events[-1])

    assert any(event.get("content") == "Hello " for event in content_events)
    assert any(event.get("content") == "world" for event in content_events)
    assert final_event.get("done") is True
    assert final_event.get("result") == "Hello world"
