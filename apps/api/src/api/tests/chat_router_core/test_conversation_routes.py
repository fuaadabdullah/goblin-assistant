"""Conversation Routes tests for chat_router."""

from unittest.mock import AsyncMock, MagicMock, patch

from .conftest import _payload


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
