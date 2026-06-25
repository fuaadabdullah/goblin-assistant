"""Tests for chat_router module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth.router import get_current_user
from api.chat_router import router


def _payload(response):
    body = response.json()
    return body["data"] if isinstance(body, dict) and "data" in body else body


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return MagicMock(id="user_123", email="test@example.com")


@pytest.fixture
def app(mock_user):
    """FastAPI app wired with the chat router and an auth override.

    Uses `dependency_overrides` (the FastAPI-blessed pattern) rather than
    monkeypatching the module attribute — `Depends(get_current_user)`
    captures the function at registration, so attribute patches don't
    actually take effect.
    """
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestCreateConversation:
    """Tests for POST /api/v1/chat/conversations endpoint."""

    def test_create_conversation_success(self, client):
        """Test successful conversation creation."""
        with patch("api.chat_router.conversation_store") as mock_store:
            mock_store.create_conversation = AsyncMock(
                return_value=MagicMock(
                    conversation_id="conv_123",
                    title="New Chat",
                    created_at=MagicMock(isoformat=lambda: "2026-05-06T00:00:00Z"),
                )
            )

            response = client.post(
                "/api/v1/chat/conversations",
                json={"title": "New Chat"},
            )

            assert response.status_code == 200
            data = _payload(response)
            assert "conversation_id" in data
            assert data["title"] == "New Chat"

    def test_create_conversation_minimal(self, client):
        """Test conversation creation with minimal data."""
        with patch("api.chat_router.conversation_store") as mock_store:
            mock_store.create_conversation = AsyncMock(
                return_value=MagicMock(
                    conversation_id="conv_456",
                    title="Chat",
                    created_at=MagicMock(isoformat=lambda: "2026-05-06T00:00:00Z"),
                )
            )

            response = client.post(
                "/api/v1/chat/conversations",
                json={},
            )

            assert response.status_code == 200


class TestListConversations:
    """Tests for GET /api/v1/chat/conversations endpoint."""

    def test_list_conversations_success(self, client):
        """Test successful conversation listing."""
        with patch("api.chat_router.conversation_store") as mock_store:
            mock_conv1 = MagicMock(
                conversation_id="conv_1",
                user_id="user_123",
                title="Chat 1",
                messages=[],
                metadata={},
                created_at=MagicMock(isoformat=lambda: "2026-05-06T00:00:00Z"),
                updated_at=MagicMock(isoformat=lambda: "2026-05-06T00:00:00Z"),
            )
            mock_store.list_conversations = AsyncMock(return_value=[mock_conv1])

            response = client.get("/api/v1/chat/conversations")

            assert response.status_code == 200
            data = _payload(response)
            assert isinstance(data, list)

    def test_list_conversations_empty(self, client):
        """Test listing with no conversations."""
        with patch("api.chat_router.conversation_store") as mock_store:
            mock_store.list_conversations = AsyncMock(return_value=[])

            response = client.get("/api/v1/chat/conversations")

            assert response.status_code == 200
            data = _payload(response)
            assert data == []


class TestGetConversation:
    """Tests for GET /api/v1/chat/conversations/{conversation_id} endpoint."""

    def test_get_conversation_success(self, client):
        """Test successful conversation retrieval."""
        conv_id = "conv_123"

        with patch("api.chat_router.conversation_store") as mock_store:
            mock_conv = MagicMock(
                conversation_id=conv_id,
                user_id="user_123",
                title="Test Chat",
                messages=[],
                created_at=MagicMock(isoformat=lambda: "2026-05-06T00:00:00Z"),
                updated_at=MagicMock(isoformat=lambda: "2026-05-06T00:00:00Z"),
                metadata={},
            )
            mock_store.get_conversation = AsyncMock(return_value=mock_conv)

            response = client.get(f"/api/v1/chat/conversations/{conv_id}")

            assert response.status_code == 200
            data = _payload(response)
            assert data["conversation_id"] == conv_id

    def test_get_conversation_not_found(self, client):
        """Test retrieval of non-existent conversation."""
        with patch("api.chat_router.conversation_store") as mock_store:
            mock_store.get_conversation = AsyncMock(return_value=None)

            response = client.get("/api/v1/chat/conversations/invalid_id")

            assert response.status_code == 404

    def test_get_conversation_not_owned(self, client):
        """Test retrieval of conversation owned by other user."""
        with patch("api.chat_router.conversation_store") as mock_store:
            mock_conv = MagicMock(
                conversation_id="conv_123",
                user_id="other_user",
                title="Other Chat",
            )
            mock_store.get_conversation = AsyncMock(return_value=mock_conv)

            response = client.get("/api/v1/chat/conversations/conv_123")

            assert response.status_code == 404


class TestUpdateConversationTitle:
    """Tests for PUT /api/v1/chat/conversations/{conversation_id}/title endpoint."""

    def test_update_title_success(self, client):
        """Test successful title update."""
        with patch("api.chat_router.conversation_store") as mock_store:
            mock_store.check_conversation_owner = AsyncMock(return_value=True)
            mock_store.update_conversation_title = AsyncMock(return_value=True)

            response = client.put(
                "/api/v1/chat/conversations/conv_123/title",
                json={"title": "Updated Title"},
            )

            assert response.status_code == 200

    def test_update_title_not_found(self, client):
        """Test title update for non-existent conversation."""
        with patch("api.chat_router.conversation_store") as mock_store:
            mock_store.check_conversation_owner = AsyncMock(return_value=False)

            response = client.put(
                "/api/v1/chat/conversations/invalid_id/title",
                json={"title": "New Title"},
            )

            assert response.status_code == 404


class TestDeleteConversation:
    """Tests for DELETE /api/v1/chat/conversations/{conversation_id} endpoint."""

    def test_delete_conversation_success(self, client):
        """Test successful conversation deletion."""
        with patch("api.chat_router.conversation_store") as mock_store:
            mock_store.check_conversation_owner = AsyncMock(return_value=True)
            mock_store.delete_conversation = AsyncMock(return_value=True)

            response = client.delete("/api/v1/chat/conversations/conv_123")

            assert response.status_code == 200

    def test_delete_conversation_not_found(self, client):
        """Test deletion of non-existent conversation."""
        with patch("api.chat_router.conversation_store") as mock_store:
            mock_store.check_conversation_owner = AsyncMock(return_value=False)

            response = client.delete("/api/v1/chat/conversations/invalid_id")

            assert response.status_code == 404


class TestLatestSnippet:
    """Tests for _latest_snippet helper function."""

    def test_latest_snippet_empty(self):
        """Test snippet from empty conversation."""
        from api.chat_router import _latest_snippet

        mock_conv = MagicMock(messages=[])
        result = _latest_snippet(mock_conv)
        assert result is None

    def test_latest_snippet_short(self):
        """Test snippet from short message."""
        from api.chat_router import _latest_snippet

        mock_msg = MagicMock(content="Short message")
        mock_conv = MagicMock(messages=[mock_msg])
        result = _latest_snippet(mock_conv)
        assert result == "Short message"

    def test_latest_snippet_long(self):
        """Test snippet from long message."""
        from api.chat_router import _latest_snippet

        long_content = "a" * 200
        mock_msg = MagicMock(content=long_content)
        mock_conv = MagicMock(messages=[mock_msg])
        result = _latest_snippet(mock_conv)

        assert result.endswith("...")
        assert len(result) == 160


class TestExtractUsageAndCost:
    """Tests for _extract_usage_and_cost helper."""

    def test_extract_usage_and_cost_success(self):
        """Test successful extraction."""
        from api.chat_router import _extract_usage_and_cost

        provider_response = {
            "result": {
                "raw": {
                    "usage": {"tokens": 100},
                    "cost_usd": 0.05,
                    "correlation_id": "corr_123",
                }
            }
        }

        usage, cost, corr_id = _extract_usage_and_cost(provider_response)

        assert usage == {"tokens": 100}
        assert cost == 0.05
        assert corr_id == "corr_123"

    def test_extract_usage_and_cost_none(self):
        """Test extraction with no data."""
        from api.chat_router import _extract_usage_and_cost

        usage, cost, corr_id = _extract_usage_and_cost(None)

        assert usage is None
        assert cost is None
        assert corr_id is None

    def test_extract_usage_and_cost_missing_fields(self):
        """Test extraction with missing fields."""
        from api.chat_router import _extract_usage_and_cost

        provider_response = {"result": {"raw": {}}}

        usage, cost, corr_id = _extract_usage_and_cost(provider_response)

        assert usage is None
        assert cost is None
        assert corr_id is None


class TestRaiseStructuredProviderError:
    """Tests for _raise_structured_provider_error helper."""

    def test_auth_error(self):
        """Test auth error handling."""
        from api.chat_router import _raise_structured_provider_error
        from api.providers.base import ProviderErrorCategory

        with pytest.raises(Exception) as exc_info:
            _raise_structured_provider_error(
                {
                    "error": "Invalid API key",
                    "error_category": ProviderErrorCategory.AUTH.value,
                    "provider": "openai",
                }
            )

        assert exc_info.value.status_code == 401

    def test_rate_limit_error(self):
        """Test rate limit error handling."""
        from api.chat_router import _raise_structured_provider_error
        from api.providers.base import ProviderErrorCategory

        with pytest.raises(Exception) as exc_info:
            _raise_structured_provider_error(
                {
                    "error": "Rate limited",
                    "error_category": ProviderErrorCategory.RATE_LIMIT.value,
                    "provider": "openai",
                }
            )

        assert exc_info.value.status_code == 429

    def test_timeout_error(self):
        """Test timeout error handling."""
        from api.chat_router import _raise_structured_provider_error
        from api.providers.base import ProviderErrorCategory

        with pytest.raises(Exception) as exc_info:
            _raise_structured_provider_error(
                {
                    "error": "Request timeout",
                    "error_category": ProviderErrorCategory.TIMEOUT.value,
                    "provider": "openai",
                }
            )

        assert exc_info.value.status_code == 504

    def test_model_error(self):
        """Test model error handling."""
        from api.chat_router import _raise_structured_provider_error
        from api.providers.base import ProviderErrorCategory

        with pytest.raises(Exception) as exc_info:
            _raise_structured_provider_error(
                {
                    "error": "Model not found",
                    "error_category": ProviderErrorCategory.MODEL_ERROR.value,
                    "provider": "openai",
                }
            )

        assert exc_info.value.status_code == 400


class TestRequestModels:
    """Tests for request/response models."""

    def test_send_message_request(self):
        """Test SendMessageRequest model."""
        from api.chat_router import SendMessageRequest

        req = SendMessageRequest(
            message="Hello",
            provider="openai",
            model="gpt-4",
            stream=False,
        )

        assert req.message == "Hello"
        assert req.provider == "openai"
        assert req.model == "gpt-4"
        assert req.stream is False

    def test_create_conversation_request(self):
        """Test CreateConversationRequest model."""
        from api.chat_router import CreateConversationRequest

        req = CreateConversationRequest(user_id="user_123", title="My Chat")

        assert req.user_id == "user_123"
        assert req.title == "My Chat"

    def test_sse_error_event(self):
        """Test SSEErrorEvent model."""
        from api.chat_router import SSEErrorEvent

        event = SSEErrorEvent(
            code="provider-timeout",
            message="Provider timed out",
            is_recoverable=True,
        )

        assert event.type == "error"
        assert event.code == "provider-timeout"
        assert event.is_recoverable is True

    def test_sse_data_event(self):
        """Test SSEDataEvent model."""
        from api.chat_router import SSEDataEvent

        event = SSEDataEvent(
            content="Hello",
            token_count=5,
            done=False,
        )

        assert event.content == "Hello"
        assert event.token_count == 5
        assert event.done is False


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


class TestEstimateTokens:
    """Tests for POST /api/v1/chat/estimate-tokens — read-only token/cost preview."""

    @staticmethod
    def _stub_assembly_service(total_tokens: int, layers: list[dict]):
        mock_layers = []
        for layer in layers:
            ml = MagicMock()
            # MagicMock(name=...) sets the mock's repr-name, not an attribute,
            # so assign after construction.
            ml.name = layer["name"]
            ml.tokens = layer["tokens"]
            mock_layers.append(ml)
        service = MagicMock()
        service.assemble_context = AsyncMock(
            return_value={
                "context": "stub",
                "layers": mock_layers,
                "total_tokens_used": total_tokens,
            }
        )
        return service

    @staticmethod
    def _stub_provider(cost_in=1.0, cost_out=2.0):
        provider = MagicMock()
        provider.COST_INPUT_PER_1K = cost_in
        provider.COST_OUTPUT_PER_1K = cost_out
        provider.estimate_cost = lambda i, o: i * cost_in / 1000 + o * cost_out / 1000
        return provider

    def test_estimate_tokens_no_conversation(self, client):
        service = self._stub_assembly_service(
            total_tokens=1000,
            layers=[
                {"name": "system", "tokens": 300},
                {"name": "ephemeral", "tokens": 700},
            ],
        )
        provider = self._stub_provider(cost_in=1.0, cost_out=2.0)

        with (
            patch(
                "api.chat_router.messages._get_context_assembly_service",
                return_value=service,
            ),
            patch(
                "api.chat_router.messages.dispatcher.get_provider",
                return_value=provider,
            ),
            patch(
                "api.chat_router.messages.dispatcher._candidate_order",
                return_value=["openai"],
            ),
        ):
            response = client.post(
                "/api/v1/chat/estimate-tokens",
                json={"message": "hello", "provider": "openai"},
            )

        assert response.status_code == 200
        data = _payload(response)
        assert data["input_tokens"] == 1000
        assert data["estimated_output_tokens"] == 400
        # 1000 * 1.0/1000 + 400 * 2.0/1000 = 1.0 + 0.8 = 1.8
        assert data["estimated_cost_usd"] == pytest.approx(1.8)
        # Response is department-based now; provider no longer surfaced.
        assert data["department"] == "general"
        assert len(data["layers"]) == 2
        assert data["layers"][0] == {"name": "system", "tokens": 300}

    def test_estimate_tokens_with_conversation_passes_history(self, client, mock_user):
        owned = MagicMock(
            user_id=mock_user.id,
            messages=[MagicMock(role="user", content=f"msg-{i}") for i in range(15)],
        )
        service = self._stub_assembly_service(total_tokens=500, layers=[])

        async def fake_require(*_a, **_k):
            return owned

        with (
            patch(
                "api.chat_router._require_owned_conversation",
                side_effect=fake_require,
            ),
            patch(
                "api.chat_router.messages._get_context_assembly_service",
                return_value=service,
            ),
            patch(
                "api.chat_router.messages.dispatcher.get_provider",
                return_value=self._stub_provider(),
            ),
            patch(
                "api.chat_router.messages.dispatcher._candidate_order",
                return_value=["openai"],
            ),
        ):
            response = client.post(
                "/api/v1/chat/estimate-tokens?conversation_id=conv-1",
                json={"message": "hello"},
            )

        assert response.status_code == 200
        # Last-10 slice should have been passed to assemble_context
        call_kwargs = service.assemble_context.call_args.kwargs
        assert len(call_kwargs["conversation_history"]) == 10
        assert call_kwargs["conversation_history"][0]["content"] == "msg-5"
        assert call_kwargs["conversation_id"] == "conv-1"

    def test_estimate_tokens_rejects_unowned_conversation(self, client):
        async def fake_require(*_a, **_k):
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Conversation not found")

        with patch(
            "api.chat_router._require_owned_conversation",
            side_effect=fake_require,
        ):
            response = client.post(
                "/api/v1/chat/estimate-tokens?conversation_id=conv-other",
                json={"message": "hello"},
            )

        assert response.status_code == 404

    def test_estimate_tokens_never_invokes_provider(self, client):
        service = self._stub_assembly_service(
            total_tokens=100, layers=[{"name": "system", "tokens": 100}]
        )

        invoke_calls = []

        async def fake_invoke(*args, **kwargs):
            invoke_calls.append((args, kwargs))
            return {"ok": True}

        with (
            patch(
                "api.chat_router.messages._get_context_assembly_service",
                return_value=service,
            ),
            patch(
                "api.chat_router.messages.dispatcher.get_provider",
                return_value=self._stub_provider(),
            ),
            patch(
                "api.chat_router.messages.dispatcher._candidate_order",
                return_value=["openai"],
            ),
            patch(
                "api.chat_router.invoke_provider",
                side_effect=fake_invoke,
            ),
        ):
            response = client.post(
                "/api/v1/chat/estimate-tokens",
                json={"message": "hello", "provider": "openai"},
            )

        assert response.status_code == 200
        assert invoke_calls == []

    def test_estimate_tokens_handles_no_configured_providers(self, client):
        service = self._stub_assembly_service(
            total_tokens=50, layers=[{"name": "system", "tokens": 50}]
        )

        with (
            patch(
                "api.chat_router.messages._get_context_assembly_service",
                return_value=service,
            ),
            patch(
                "api.chat_router.messages.dispatcher._candidate_order",
                return_value=[],
            ),
        ):
            response = client.post(
                "/api/v1/chat/estimate-tokens",
                json={"message": "hello"},
            )

        assert response.status_code == 200
        data = _payload(response)
        # Response is department-based now; provider no longer surfaced.
        assert data["department"] == "general"
        assert data["estimated_cost_usd"] == 0.0
        assert data["degraded_mode"] is True
        assert data["degraded_reason"] == "no-configured-providers"


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
