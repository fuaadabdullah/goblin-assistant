"""Send Message Archiving tests for chat_router."""

from unittest.mock import AsyncMock, MagicMock, patch


class TestSendMessageArchiving:
    """Tests archive scheduling behavior for send-message route."""

    def test_send_message_schedules_archiving_after_user_and_assistant_writes(
        self, client, mock_user
    ):
        conversation_id = "conv-archive-1"
        schedule_calls = []

        owned_conversation = MagicMock(
            conversation_id=conversation_id,
            user_id=mock_user.id,
            messages=[MagicMock(role="user", content="hello")],
        )

        async def fake_require_owned_conversation(*_args, **_kwargs):
            return owned_conversation

        async def fake_process_message(*_args, **_kwargs):
            return {
                "classification": {"type": "working", "confidence": 1.0},
                "decision": {"actions": [], "confidence": 1.0},
                "execution": {"actions_executed": []},
                "processed_at": "2026-03-07T12:00:00.000000",
            }

        async def fake_schedule(conversation_id_arg: str):
            schedule_calls.append(conversation_id_arg)

        async def fake_invoke_provider(pid, model, payload, timeout_ms, stream=False):
            return {
                "ok": True,
                "provider": pid or "openai",
                "model": model or "gpt-4o-mini",
                "result": {"text": "assistant response", "raw": {}},
            }

        mock_wti = MagicMock()
        mock_wti.process_message = AsyncMock(side_effect=fake_process_message)

        with (
            patch(
                "api.chat_router._require_owned_conversation",
                side_effect=fake_require_owned_conversation,
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
                side_effect=fake_invoke_provider,
            ),
            patch(
                "api.chat_router.messages.schedule_conversation_archive",
                side_effect=fake_schedule,
            ),
        ):
            response = client.post(
                f"/api/v1/chat/conversations/{conversation_id}/messages",
                json={
                    "message": "hello",
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
            )

        assert response.status_code == 200
        assert schedule_calls == [conversation_id, conversation_id]

    def test_send_message_records_task_history_and_usage_event(self, client, mock_user):
        conversation_id = "conv-usage-1"

        owned_conversation = MagicMock(
            conversation_id=conversation_id,
            user_id=mock_user.id,
            messages=[MagicMock(role="user", content="hello")],
        )

        async def fake_require_owned_conversation(*_args, **_kwargs):
            return owned_conversation

        async def fake_invoke_provider(pid, model, payload, timeout_ms, stream=False):
            _ = (pid, model, payload, timeout_ms, stream)
            return {
                "ok": True,
                "provider": "openai",
                "model": "gpt-4o-mini",
                "result": {
                    "text": "assistant response",
                    "raw": {
                        "usage": {
                            "prompt_tokens": 40,
                            "completion_tokens": 10,
                            "total_tokens": 50,
                        },
                        "cost_usd": 0.003,
                    },
                },
            }

        mock_wti = MagicMock()
        mock_wti.process_message = AsyncMock(
            return_value={
                "classification": {"type": "working", "confidence": 1.0},
                "decision": {"actions": [], "confidence": 1.0},
                "execution": {"actions_executed": []},
                "processed_at": "2026-03-07T12:00:00.000000",
            }
        )

        fake_task_store = MagicMock()
        fake_task_store.save_task = AsyncMock()

        fake_usage_store = MagicMock()
        fake_usage_store.check_limits = AsyncMock(return_value={"allowed": True})
        fake_usage_store.save_event = AsyncMock()

        with (
            patch(
                "api.chat_router._require_owned_conversation",
                side_effect=fake_require_owned_conversation,
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
                side_effect=fake_invoke_provider,
            ),
            patch(
                "api.chat_router.messages.get_task_store",
                new_callable=AsyncMock,
                return_value=fake_task_store,
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
            ),
        ):
            response = client.post(
                f"/api/v1/chat/conversations/{conversation_id}/messages",
                json={
                    "message": "hello",
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
            )

        assert response.status_code == 200
        fake_task_store.save_task.assert_awaited_once()
        fake_usage_store.save_event.assert_awaited_once()
