"""Contextual Chat Route tests for chat_router."""

from unittest.mock import AsyncMock, MagicMock, patch

from .conftest import _payload


class TestContextualChatRoute:
    """Route-level contextual chat coverage for provider routing + RAG metadata."""

    def test_contextual_chat_surfaces_fallback_provider_and_degraded_rag_state(
        self,
        client,
        mock_user,
    ):
        owned_conversation = MagicMock(
            user_id=mock_user.id,
            messages=[
                MagicMock(role="user", content="Earlier question"),
                MagicMock(role="assistant", content="Earlier answer"),
            ],
        )

        assembly_result = {
            "context": "[SEMANTIC_RETRIEVAL]\nretrieved\n\n[EPHEMERAL_MEMORY]\nrecent",
            "layers": [],
            "total_tokens_used": 180,
            "remaining_tokens": 820,
            "assembly_log": {"assembly_time": "2026-06-04T00:00:00Z"},
            "degraded_mode": True,
            "degraded_reason": "embedding unavailable; context_truncated:semantic_retrieval_truncated",
            "truncation_warnings": ["semantic_retrieval_truncated"],
            "summary_fallback_applied": False,
        }
        service = MagicMock(assemble_context=AsyncMock(return_value=assembly_result))
        fake_worker = MagicMock(queue_message_embedding=AsyncMock())
        stored_messages = []

        async def fake_add_message_to_conversation(**kwargs):
            stored_messages.append(kwargs)
            return True

        with (
            patch(
                "api.chat_router.contextual._cr._assert_conversation_owned",
                new_callable=AsyncMock,
                return_value=owned_conversation,
            ),
            patch(
                "api.chat_router.conversation_store.get_conversation",
                new_callable=AsyncMock,
                return_value=owned_conversation,
            ),
            patch(
                "api.chat_router.conversation_store.add_message_to_conversation",
                new_callable=AsyncMock,
                side_effect=fake_add_message_to_conversation,
            ),
            patch(
                "api.chat_router.contextual._get_context_assembly_service",
                return_value=service,
            ),
            patch(
                "api.chat_router.contextual.export_tools_for_provider",
                return_value=[],
            ),
            patch(
                "api.chat_router.contextual._cr.invoke_provider",
                new_callable=AsyncMock,
                return_value={
                    "ok": True,
                    "provider": "groq",
                    "model": "llama-3.3-70b-versatile",
                    "result": {"text": "fallback answer"},
                },
            ),
            patch(
                "api.chat_router.contextual._get_embedding_worker",
                return_value=fake_worker,
            ),
            patch(
                "api.chat_router.contextual.schedule_conversation_archive",
                new_callable=AsyncMock,
            ),
        ):
            response = client.post(
                "/api/v1/chat/contextual-chat",
                json={
                    "message": "What changed?",
                    "conversation_id": "conv_123",
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "enable_context_assembly": True,
                },
            )

        assert response.status_code == 200
        data = _payload(response)
        assert data["response"] == "fallback answer"
        # provider/model moved off the response envelope (department-based API);
        # the provider that actually answered is asserted via stored_messages below.
        assert data["token_usage"]["degraded_mode"] is True
        assert data["token_usage"]["degraded_reason"].startswith("embedding unavailable")
        assert data["token_usage"]["truncation_warnings"] == ["semantic_retrieval_truncated"]

        call_kwargs = service.assemble_context.call_args.kwargs
        assert call_kwargs["conversation_id"] == "conv_123"
        assert call_kwargs["conversation_history"] == [
            {"role": "user", "content": "Earlier question"},
            {"role": "assistant", "content": "Earlier answer"},
        ]

        assert len(stored_messages) == 2
        assert stored_messages[1]["metadata"]["provider"] == "groq"
        assert stored_messages[1]["metadata"]["model"] == "llama-3.3-70b-versatile"
        assert stored_messages[1]["metadata"]["token_usage"]["degraded_mode"] is True
        assert fake_worker.queue_message_embedding.await_count == 2
