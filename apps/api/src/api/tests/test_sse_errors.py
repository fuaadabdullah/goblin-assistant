"""Integration tests for SSE error handling in chat streaming."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from api.auth.router import User as AuthenticatedUser
from api.chat_router import generate_chat_stream
from api.chat_router.streaming import _format_unhandled_stream_error
from api.storage.conversations import Conversation


@pytest.fixture(name="authenticated_user")
def authenticated_user_fixture():
    return AuthenticatedUser(
        id="test-user-id",
        email="test@example.com",
        name="Test User",
    )


@pytest.fixture(name="test_conversation")
def test_conversation_fixture():
    return Conversation(
        conversation_id="test-conv-id",
        user_id="test-user-id",
        title="Test Conversation",
        messages=[],
    )


def parse_sse_event(frame: str) -> dict:
    """Extract the JSON payload from an SSE frame.

    Accepts both single-line (`data: {...}`) and multi-line
    (`event: X\\ndata: {...}\\n\\n`) frames so tests are insensitive to
    whether the emitter sets an explicit event name.
    """
    for line in frame.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return {}


def _parsed_events(events):
    parsed = (parse_sse_event(item) for item in events)
    return [event for event in parsed if event]


def _error_events(events):
    return [event for event in _parsed_events(events) if event.get("code")]


def _content_events(events):
    return [event for event in _parsed_events(events) if "content" in event]


def test_unhandled_stream_error_formatter_preserves_message():
    assert _format_unhandled_stream_error(RuntimeError("boom")) == "boom"
    assert _format_unhandled_stream_error(RuntimeError("")) == (
        "An unexpected error occurred. Your message was saved if it got this far."
    )


@pytest.mark.asyncio
async def test_auth_failure_returns_error_event(authenticated_user):
    with patch(
        "api.chat_router._require_owned_conversation",
        side_effect=HTTPException(status_code=401, detail="Unauthorized"),
    ):
        events = []
        async for event in generate_chat_stream(
            message="test",
            conversation_id="wrong-conv-id",
            current_user=authenticated_user,
        ):
            events.append(event)

    error_events = _error_events(events)

    assert error_events
    assert any(event.get("code") == "auth-failed" for event in error_events)
    assert all(event.get("is_recoverable") is False for event in error_events)


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_non_streaming_ok_response_emits_content_and_completion(
    authenticated_user,
    test_conversation,
):
    provider_response = {
        "ok": True,
        "result": {"text": "Direct response"},
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

    assert any(event.get("content") == "Direct response" for event in content_events)
    assert final_event.get("done") is True
    assert final_event.get("result") == "Direct response"


@pytest.mark.asyncio
async def test_assistant_message_storage_failure_emits_warning(
    authenticated_user,
    test_conversation,
):
    provider_response = {
        "ok": True,
        "result": {"text": "Save me"},
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
            side_effect=[True, Exception("DB write failed")],
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

    error_events = _error_events(events)
    content_events = _content_events(events)

    assert any(event.get("content") == "Save me" for event in content_events)
    assert any(event.get("code") == "response-storage-failed" for event in error_events)
    assert any(event.get("type") == "warning" for event in error_events)


@pytest.mark.asyncio
async def test_malformed_non_dict_provider_response_falls_back_to_error(
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
            side_effect=["not-a-dict", {"ok": False, "error": "fallback failed"}],
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
        event.get("details", {}).get("provider_error") == "provider-error" for event in error_events
    )


@pytest.mark.asyncio
async def test_streaming_emits_chat_message_created_for_assistant(
    authenticated_user,
    test_conversation,
):
    """Streaming path must emit chat.message.created after persisting the assistant message."""
    provider_response = {
        "ok": True,
        "result": {"text": "Hello from stream"},
        "provider": "test-provider",
        "model": "test-model",
    }

    emit_mock = AsyncMock(return_value=None)

    with (
        patch(
            "api.chat_router._require_owned_conversation",
            return_value=test_conversation,
        ),
        patch(
            "api.chat_router.InputSanitizer.sanitize_chat_message",
            return_value=("hello", None),
        ),
        patch(
            "api.chat_router.conversation_store.add_message_to_conversation",
            new_callable=AsyncMock,
        ),
        patch(
            "api.chat_router.invoke_provider",
            return_value=provider_response,
        ),
        patch(
            "api.chat_router.streaming.event_emitter.emit",
            emit_mock,
        ),
        patch(
            "api.chat_router.streaming.schedule_conversation_archive",
            new_callable=AsyncMock,
        ),
    ):
        events = []
        async for event in generate_chat_stream(
            message="hello",
            conversation_id="test-conv-id",
            current_user=authenticated_user,
        ):
            events.append(event)

    final_event = parse_sse_event(events[-1])
    assert final_event.get("done") is True

    emit_mock.assert_awaited_once()
    call_args = emit_mock.call_args
    assert call_args.args[0] == "chat.message.created"
    payload = call_args.kwargs["payload"]
    assert payload.role == "assistant"
    assert payload.conversation_id == "test-conv-id"
    assert payload.provider == "test-provider"
    assert payload.model == "test-model"


@pytest.mark.asyncio
async def test_streaming_does_not_emit_when_assistant_message_fails_to_save(
    authenticated_user,
    test_conversation,
):
    """event_emitter must NOT fire if the DB write for the assistant message raised."""
    provider_response = {
        "ok": True,
        "result": {"text": "fail to save"},
        "provider": "test-provider",
        "model": "test-model",
    }

    emit_mock = AsyncMock(return_value=None)

    with (
        patch(
            "api.chat_router._require_owned_conversation",
            return_value=test_conversation,
        ),
        patch(
            "api.chat_router.InputSanitizer.sanitize_chat_message",
            return_value=("hello", None),
        ),
        patch(
            "api.chat_router.conversation_store.add_message_to_conversation",
            side_effect=[True, Exception("DB down")],
        ),
        patch(
            "api.chat_router.invoke_provider",
            return_value=provider_response,
        ),
        patch(
            "api.chat_router.streaming.event_emitter.emit",
            emit_mock,
        ),
    ):
        events = []
        async for event in generate_chat_stream(
            message="hello",
            conversation_id="test-conv-id",
            current_user=authenticated_user,
        ):
            events.append(event)

    emit_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_streaming_records_provider_and_model_from_response(
    authenticated_user,
    test_conversation,
):
    """used_provider/used_model must be taken from the provider_response dict,
    not left as the caller-supplied defaults.  Regression for the bug where
    the stream branch never updated these from provider_response."""

    async def mock_stream_gen():
        yield {"text": "hello"}

    provider_response = {
        "ok": True,
        "stream": mock_stream_gen(),
        "provider": "siliconeflow",
        "model": "Qwen/Qwen2.5-7B-Instruct",
    }

    add_msg_mock = AsyncMock(return_value=None)
    emit_mock = AsyncMock(return_value=None)

    with (
        patch(
            "api.chat_router._require_owned_conversation",
            return_value=test_conversation,
        ),
        patch(
            "api.chat_router.InputSanitizer.sanitize_chat_message",
            return_value=("hello", None),
        ),
        patch(
            "api.chat_router.conversation_store.add_message_to_conversation",
            add_msg_mock,
        ),
        patch(
            "api.chat_router.invoke_provider",
            return_value=provider_response,
        ),
        patch(
            "api.chat_router.streaming.event_emitter.emit",
            emit_mock,
        ),
        patch(
            "api.chat_router.streaming.schedule_conversation_archive",
            new_callable=AsyncMock,
        ),
    ):
        async for _ in generate_chat_stream(
            message="hello",
            conversation_id="test-conv-id",
            current_user=authenticated_user,
        ):
            continue

    # The assistant message stored in the DB must carry the real provider/model.
    asst_call = next(
        (c for c in add_msg_mock.call_args_list if c.kwargs.get("role") == "assistant"),
        None,
    )
    assert asst_call is not None, "assistant message was never persisted"
    metadata = asst_call.kwargs.get("metadata", {})
    assert metadata.get("provider") == "siliconeflow"
    assert metadata.get("model") == "Qwen/Qwen2.5-7B-Instruct"

    # The domain event must also carry the real provider/model.
    emit_mock.assert_awaited_once()
    payload = emit_mock.call_args.kwargs["payload"]
    assert payload.provider == "siliconeflow"
    assert payload.model == "Qwen/Qwen2.5-7B-Instruct"
