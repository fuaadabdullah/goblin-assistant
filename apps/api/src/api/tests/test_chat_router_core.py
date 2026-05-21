"""Tests for chat_router module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.auth.router import get_current_user
from api.chat_router import router


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
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestCreateConversation:
    """Tests for POST /chat/conversations endpoint."""

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
                "/chat/conversations",
                json={"title": "New Chat"},
            )

            assert response.status_code == 200
            data = response.json()
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
                "/chat/conversations",
                json={},
            )

            assert response.status_code == 200


class TestListConversations:
    """Tests for GET /chat/conversations endpoint."""

    def test_list_conversations_success(self, client):
        """Test successful conversation listing."""
        with patch("api.chat_router.conversation_store") as mock_store:
            mock_conv1 = MagicMock(
                conversation_id="conv_1",
                user_id="user_123",
                title="Chat 1",
                messages=[],
                created_at=MagicMock(isoformat=lambda: "2026-05-06T00:00:00Z"),
                updated_at=MagicMock(isoformat=lambda: "2026-05-06T00:00:00Z"),
            )
            mock_store.list_conversations = AsyncMock(
                return_value=[mock_conv1]
            )

            response = client.get("/chat/conversations")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_list_conversations_empty(self, client):
        """Test listing with no conversations."""
        with patch("api.chat_router.conversation_store") as mock_store:
            mock_store.list_conversations = AsyncMock(return_value=[])

            response = client.get("/chat/conversations")

            assert response.status_code == 200
            data = response.json()
            assert data == []


class TestGetConversation:
    """Tests for GET /chat/conversations/{conversation_id} endpoint."""

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

            response = client.get(f"/chat/conversations/{conv_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["conversation_id"] == conv_id

    def test_get_conversation_not_found(self, client):
        """Test retrieval of non-existent conversation."""
        with patch("api.chat_router.conversation_store") as mock_store:
            mock_store.get_conversation = AsyncMock(return_value=None)

            response = client.get("/chat/conversations/invalid_id")

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

            response = client.get("/chat/conversations/conv_123")

            assert response.status_code == 404


class TestUpdateConversationTitle:
    """Tests for PUT /chat/conversations/{conversation_id}/title endpoint."""

    def test_update_title_success(self, client):
        """Test successful title update."""
        with patch("api.chat_router.conversation_store") as mock_store:
            mock_store.check_conversation_owner = AsyncMock(return_value=True)
            mock_store.update_conversation_title = AsyncMock(return_value=True)

            response = client.put(
                "/chat/conversations/conv_123/title",
                json={"title": "Updated Title"},
            )

            assert response.status_code == 200

    def test_update_title_not_found(self, client):
        """Test title update for non-existent conversation."""
        with patch("api.chat_router.conversation_store") as mock_store:
            mock_store.check_conversation_owner = AsyncMock(return_value=False)

            response = client.put(
                "/chat/conversations/invalid_id/title",
                json={"title": "New Title"},
            )

            assert response.status_code == 404


class TestDeleteConversation:
    """Tests for DELETE /chat/conversations/{conversation_id} endpoint."""

    def test_delete_conversation_success(self, client):
        """Test successful conversation deletion."""
        with patch("api.chat_router.conversation_store") as mock_store:
            mock_store.check_conversation_owner = AsyncMock(return_value=True)
            mock_store.delete_conversation = AsyncMock(return_value=True)

            response = client.delete("/chat/conversations/conv_123")

            assert response.status_code == 200

    def test_delete_conversation_not_found(self, client):
        """Test deletion of non-existent conversation."""
        with patch("api.chat_router.conversation_store") as mock_store:
            mock_store.check_conversation_owner = AsyncMock(return_value=False)

            response = client.delete("/chat/conversations/invalid_id")

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
                    "correlation_id": "corr_123"
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
            _raise_structured_provider_error({
                "error": "Invalid API key",
                "error_category": ProviderErrorCategory.AUTH.value,
                "provider": "openai"
            })

        assert exc_info.value.status_code == 401

    def test_rate_limit_error(self):
        """Test rate limit error handling."""
        from api.chat_router import _raise_structured_provider_error
        from api.providers.base import ProviderErrorCategory

        with pytest.raises(Exception) as exc_info:
            _raise_structured_provider_error({
                "error": "Rate limited",
                "error_category": ProviderErrorCategory.RATE_LIMIT.value,
                "provider": "openai"
            })

        assert exc_info.value.status_code == 429

    def test_timeout_error(self):
        """Test timeout error handling."""
        from api.chat_router import _raise_structured_provider_error
        from api.providers.base import ProviderErrorCategory

        with pytest.raises(Exception) as exc_info:
            _raise_structured_provider_error({
                "error": "Request timeout",
                "error_category": ProviderErrorCategory.TIMEOUT.value,
                "provider": "openai"
            })

        assert exc_info.value.status_code == 504

    def test_model_error(self):
        """Test model error handling."""
        from api.chat_router import _raise_structured_provider_error
        from api.providers.base import ProviderErrorCategory

        with pytest.raises(Exception) as exc_info:
            _raise_structured_provider_error({
                "error": "Model not found",
                "error_category": ProviderErrorCategory.MODEL_ERROR.value,
                "provider": "openai"
            })

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
