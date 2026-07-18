"""Non Streaming SSE tests."""

from unittest.mock import AsyncMock, patch

from api.chat_router import generate_chat_stream

from .conftest import _content_events, _error_events, parse_sse_event


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
