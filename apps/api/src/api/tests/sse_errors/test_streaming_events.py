"""Streaming Events SSE tests."""

from unittest.mock import AsyncMock, patch

from api.chat_router import generate_chat_stream

from .conftest import parse_sse_event


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


async def test_streaming_persists_canonical_goblin_id_from_caller(
    authenticated_user,
    test_conversation,
):
    provider_response = {
        "ok": True,
        "result": {"text": "Hello from docs"},
        "provider": "test-provider",
        "model": "test-model",
    }

    add_msg_mock = AsyncMock(return_value=None)
    emit_mock = AsyncMock(return_value=None)
    task_store = AsyncMock()
    task_store.save_task = AsyncMock(return_value=None)
    usage_store = AsyncMock()
    usage_store.save_event = AsyncMock(return_value=None)

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
        patch(
            "api.chat_router.streaming.get_task_store",
            new_callable=AsyncMock,
            return_value=task_store,
        ),
        patch(
            "api.chat_router.streaming.get_usage_event_store",
            new_callable=AsyncMock,
            return_value=usage_store,
        ),
    ):
        events = []
        async for event in generate_chat_stream(
            message="hello",
            conversation_id="test-conv-id",
            current_user=authenticated_user,
            goblin_id="docs-writer",
        ):
            events.append(event)

    asst_call = next(
        (c for c in add_msg_mock.call_args_list if c.kwargs.get("role") == "assistant"),
        None,
    )
    assert asst_call is not None, "assistant message was never persisted"
    metadata = asst_call.kwargs.get("metadata", {})
    assert metadata.get("goblin_id") == "docs-writer"
    assert metadata.get("goblin") == "docs-writer"

    task_store.save_task.assert_awaited_once()
    task_payload = task_store.save_task.await_args.args[1]
    assert task_payload["metadata"]["goblin_id"] == "docs-writer"

    usage_store.save_event.assert_awaited_once()
    usage_payload = usage_store.save_event.await_args.args[0]
    assert usage_payload["metadata"]["goblin_id"] == "docs-writer"
