"""Request Models tests for chat_router."""


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
