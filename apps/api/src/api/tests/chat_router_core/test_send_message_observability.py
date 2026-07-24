"""Send Message Observability tests for chat_router."""

from unittest.mock import AsyncMock, MagicMock, patch


class TestSendMessageObservability:
    def test_provider_failure_emits_chat_message_failed_event(self, client, mock_user):
        conversation_id = "conv-provider-fail-1"
        owned_conversation = MagicMock(
            conversation_id=conversation_id,
            user_id=mock_user.id,
            messages=[MagicMock(role="user", content="hello")],
        )

        mock_wti = MagicMock()
        mock_wti.process_message = AsyncMock(
            return_value={
                "classification": {"type": "working", "confidence": 1.0},
                "decision": {"actions": [], "confidence": 1.0},
                "execution": {"actions_executed": []},
                "processed_at": "2026-03-07T12:00:00.000000",
            }
        )
        fake_usage_store = MagicMock()
        fake_usage_store.check_limits = AsyncMock(return_value={"allowed": True})

        with (
            patch(
                "api.chat_router._require_owned_conversation",
                new_callable=AsyncMock,
                return_value=owned_conversation,
            ),
            patch(
                "api.chat_router.messages._get_write_time_intelligence",
                return_value=mock_wti,
            ),
            patch(
                "api.chat_router.conversation_store.add_message_to_conversation",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "api.chat_router.invoke_provider",
                new_callable=AsyncMock,
                return_value={
                    "ok": False,
                    "error": "Request timeout",
                    "error_category": "timeout",
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
            ),
            patch(
                "api.chat_router.messages.get_usage_event_store",
                new_callable=AsyncMock,
                return_value=fake_usage_store,
            ),
            patch(
                "api.chat_router.messages.schedule_conversation_archive",
                new_callable=AsyncMock,
            ),
            patch(
                "api.chat_router.messages.event_emitter.emit",
                new_callable=AsyncMock,
            ) as mock_emit,
        ):
            response = client.post(
                f"/api/v1/chat/conversations/{conversation_id}/messages",
                json={"message": "hello", "provider": "openai", "model": "gpt-4o-mini"},
            )

        assert response.status_code == 504
        failed_calls = [
            c for c in mock_emit.await_args_list if c.args and c.args[0] == "chat.message.failed"
        ]
        assert len(failed_calls) == 1
        failed_payload = failed_calls[0].kwargs["payload"]
        assert failed_payload.stage == "provider"
        assert failed_payload.provider == "openai"
        assert failed_payload.code == "CHAT_TIMEOUT"
        assert failed_payload.status_code == 504

    def test_unhandled_error_emits_chat_message_failed_event(self, client, mock_user):
        conversation_id = "conv-unhandled-fail-1"
        owned_conversation = MagicMock(
            conversation_id=conversation_id,
            user_id=mock_user.id,
            messages=[MagicMock(role="user", content="hello")],
        )
        mock_wti = MagicMock()
        mock_wti.process_message = AsyncMock(
            return_value={
                "classification": {"type": "working", "confidence": 1.0},
                "decision": {"actions": [], "confidence": 1.0},
                "execution": {"actions_executed": []},
                "processed_at": "2026-03-07T12:00:00.000000",
            }
        )

        with (
            patch(
                "api.chat_router._require_owned_conversation",
                new_callable=AsyncMock,
                return_value=owned_conversation,
            ),
            patch(
                "api.chat_router.messages._get_write_time_intelligence",
                return_value=mock_wti,
            ),
            patch(
                "api.chat_router.conversation_store.add_message_to_conversation",
                new_callable=AsyncMock,
                side_effect=RuntimeError("db write failed"),
            ),
            patch(
                "api.chat_router.messages.event_emitter.emit",
                new_callable=AsyncMock,
            ) as mock_emit,
        ):
            response = client.post(
                f"/api/v1/chat/conversations/{conversation_id}/messages",
                json={"message": "hello", "provider": "openai", "model": "gpt-4o-mini"},
            )

        assert response.status_code == 500
        failed_calls = [
            c for c in mock_emit.await_args_list if c.args and c.args[0] == "chat.message.failed"
        ]
        assert len(failed_calls) == 1
        failed_payload = failed_calls[0].kwargs["payload"]
        assert failed_payload.stage == "unhandled"
        assert failed_payload.code == "INTERNAL_ERROR"
        assert failed_payload.status_code == 500

    def test_send_message_sets_sentry_context_when_sdk_is_available(self, client, mock_user):
        import sys
        import types

        conversation_id = "conv-sentry-1"
        owned_conversation = MagicMock(
            conversation_id=conversation_id,
            user_id=mock_user.id,
            messages=[MagicMock(role="user", content="hello")],
        )
        mock_wti = MagicMock()
        mock_wti.process_message = AsyncMock(
            return_value={
                "classification": {"type": "working", "confidence": 1.0},
                "decision": {"actions": [], "confidence": 1.0},
                "execution": {"actions_executed": []},
                "processed_at": "2026-03-07T12:00:00.000000",
            }
        )
        fake_usage_store = MagicMock()
        fake_usage_store.check_limits = AsyncMock(return_value={"allowed": True})
        fake_usage_store.save_event = AsyncMock()

        sentry_sdk = types.SimpleNamespace(
            set_tag=MagicMock(),
            set_context=MagicMock(),
            set_transaction_name=MagicMock(),
        )

        with (
            patch.dict(sys.modules, {"sentry_sdk": sentry_sdk}),
            patch(
                "api.chat_router._require_owned_conversation",
                new_callable=AsyncMock,
                return_value=owned_conversation,
            ),
            patch(
                "api.chat_router.messages._get_write_time_intelligence",
                return_value=mock_wti,
            ),
            patch(
                "api.chat_router.conversation_store.add_message_to_conversation",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "api.chat_router.invoke_provider",
                new_callable=AsyncMock,
                return_value={
                    "ok": True,
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "result": {"text": "assistant response", "raw": {}},
                },
            ),
            patch(
                "api.chat_router.messages.get_usage_event_store",
                new_callable=AsyncMock,
                return_value=fake_usage_store,
            ),
            patch(
                "api.chat_router.messages.get_task_store",
                new_callable=AsyncMock,
                return_value=MagicMock(save_task=AsyncMock()),
            ),
            patch(
                "api.chat_router.messages.schedule_conversation_archive",
                new_callable=AsyncMock,
            ),
            patch(
                "api.chat_router.messages.event_emitter.emit",
                new_callable=AsyncMock,
            ),
        ):
            response = client.post(
                f"/api/v1/chat/conversations/{conversation_id}/messages",
                json={"message": "hello", "provider": "openai", "model": "gpt-4o-mini"},
            )

        assert response.status_code == 200
        sentry_sdk.set_tag.assert_any_call("conversation_id", conversation_id)
        sentry_sdk.set_tag.assert_any_call("operation", "chat.send_message")
        sentry_sdk.set_transaction_name.assert_called_once_with(
            "POST /api/v1/chat/conversations/{conversation_id}/messages"
        )
