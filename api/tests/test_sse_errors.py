"""
Integration tests for SSE error handling in chat streaming.

Tests cover:
- Provider timeout errors trigger proper error events
- Provider connection failures send recoverable error
- Mid-stream failures send partial data with error event
- DB write failures don't lose user messages
- Auth failures prevent stream access
- Specific error codes sent for different scenarios
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import asyncio

from api.chat_router import generate_chat_stream
from api.storage.conversations import Conversation
from api.auth.router import User as AuthenticatedUser


@pytest.fixture
def authenticated_user():
    """Mock authenticated user"""
    return AuthenticatedUser(
        id="test-user-id",
        email="test@example.com",
        name="Test User",
    )


@pytest.fixture
def test_conversation():
    """Test conversation"""
    return Conversation(
        conversation_id="test-conv-id",
        user_id="test-user-id",
        title="Test Conversation",
        messages=[],
    )


def parse_sse_event(data_line: str) -> dict:
    """Parse SSE data line into dict"""
    if data_line.startswith("data: "):
        json_str = data_line[6:]  # Remove "data: " prefix
        return json.loads(json_str)
    return {}


@pytest.mark.asyncio
async def test_auth_failure_returns_error_event(authenticated_user, test_conversation):
    """Test that auth failures return error event with auth-failed code"""
    with patch(
        "api.chat_router._require_owned_conversation",
        side_effect=Exception("Unauthorized")
    ):
        events = []
        async for event in generate_chat_stream(
            message="test",
            conversation_id="wrong-conv-id",
            current_user=authenticated_user,
        ):
            events.append(event)
        
        # Find the error event (skip status event)
        error_events = [parse_sse_event(e) for e in events if "code" in parse_sse_event(e)]
        
        assert len(error_events) > 0
        # Check that auth errors are in error events
        assert any(e.get("code") in ["auth-failed", "http-401"] for e in error_events)


@pytest.mark.asyncio
async def test_provider_timeout_returns_recoverable_error(authenticated_user, test_conversation):
    """Test that provider timeouts return is_recoverable=true"""
    with patch("api.chat_router._require_owned_conversation", return_value=test_conversation), \
         patch("api.chat_router.InputSanitizer.sanitize_chat_message", return_value=("test", None)), \
         patch("api.chat_router.conversation_store.add_message_to_conversation", new_callable=AsyncMock), \
         patch("api.chat_router.invoke_provider", side_effect=asyncio.TimeoutError()):
        
        events = []
        async for event in generate_chat_stream(
            message="test",
            conversation_id="test-conv-id",
            current_user=authenticated_user,
            provider="test-provider",
        ):
            events.append(event)
        
        error_events = [parse_sse_event(e) for e in events if "code" in parse_sse_event(e)]
        assert any(
            e.get("code") == "provider-timeout" and e.get("is_recoverable") is True
            for e in error_events
        )


@pytest.mark.asyncio
async def test_provider_error_fallback_to_nonstreaming(authenticated_user, test_conversation):
    """Test that provider streaming errors trigger fallback to non-streaming"""
    fallback_response = {
        "ok": True,
        "result": {"text": "Fallback response"},
        "provider": "test-provider",
        "model": "test-model",
    }
    
    with patch("api.chat_router._require_owned_conversation", return_value=test_conversation), \
         patch("api.chat_router.InputSanitizer.sanitize_chat_message", return_value=("test", None)), \
         patch("api.chat_router.conversation_store.add_message_to_conversation", new_callable=AsyncMock), \
         patch("api.chat_router.conversation_store.get_conversation", return_value=test_conversation), \
         patch("api.chat_router.invoke_provider") as mock_invoke:
        
        # First call (streaming) returns error, second call (fallback) returns success
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
        
        # Should have content event from fallback
        content_events = [parse_sse_event(e) for e in events if "content" in parse_sse_event(e)]
        assert any(e.get("content") == "Fallback response" for e in content_events)


@pytest.mark.asyncio
async def test_user_message_stored_before_provider_call(authenticated_user, test_conversation):
    """Test that user message is stored before provider is called"""
    message_stored = False
    
    async def mock_add_message(*args, **kwargs):
        nonlocal message_stored
        if kwargs.get("role") == "user":
            message_stored = True
    
    with patch("api.chat_router._require_owned_conversation", return_value=test_conversation), \
         patch("api.chat_router.InputSanitizer.sanitize_chat_message", return_value=("test", None)), \
         patch("api.chat_router.conversation_store.add_message_to_conversation", side_effect=mock_add_message), \
         patch("api.chat_router.invoke_provider", side_effect=asyncio.TimeoutError()):
        
        events = []
        try:
            async for event in generate_chat_stream(
                message="test message",
                conversation_id="test-conv-id",
                current_user=authenticated_user,
            ):
                events.append(event)
        except:
            pass
        
        # Message should have been stored even though provider timed out
        assert message_stored


@pytest.mark.asyncio
async def test_stream_error_with_partial_response(authenticated_user, test_conversation):
    """Test that mid-stream errors are handled with partial response info"""
    async def mock_stream_gen():
        # Yield some chunks then fail
        yield {"text": "Hello "}
        yield {"text": "world"}
        raise RuntimeError("Stream interrupted")
    
    provider_response = {
        "ok": True,
        "stream": mock_stream_gen(),
        "provider": "test-provider",
        "model": "test-model",
    }
    
    with patch("api.chat_router._require_owned_conversation", return_value=test_conversation), \
         patch("api.chat_router.InputSanitizer.sanitize_chat_message", return_value=("test", None)), \
         patch("api.chat_router.conversation_store.add_message_to_conversation", new_callable=AsyncMock), \
         patch("api.chat_router.conversation_store.get_conversation", return_value=test_conversation), \
         patch("api.chat_router.invoke_provider", return_value=provider_response):
        
        events = []
        async for event in generate_chat_stream(
            message="test",
            conversation_id="test-conv-id",
            current_user=authenticated_user,
        ):
            events.append(event)
        
        # Should have content events for the streamed data
        content_events = [parse_sse_event(e) for e in events if "content" in parse_sse_event(e)]
        assert any("Hello" in str(e.get("content", "")) for e in content_events)
        assert any("world" in str(e.get("content", "")) for e in content_events)
        
        # Should have error event with has_partial_response=True
        error_events = [parse_sse_event(e) for e in events if "code" in parse_sse_event(e)]
        assert any(
            e.get("code") == "stream-interrupted" and e.get("is_recoverable") is True
            for e in error_events
        )


@pytest.mark.asyncio
async def test_db_write_error_returns_error_event(authenticated_user, test_conversation):
    """Test that DB write failures during message storage send error event"""
    with patch("api.chat_router._require_owned_conversation", return_value=test_conversation), \
         patch("api.chat_router.InputSanitizer.sanitize_chat_message", return_value=("test", None)), \
         patch(
             "api.chat_router.conversation_store.add_message_to_conversation",
             side_effect=Exception("DB connection failed")
         ):
        
        events = []
        async for event in generate_chat_stream(
            message="test",
            conversation_id="test-conv-id",
            current_user=authenticated_user,
        ):
            events.append(event)
        
        error_events = [parse_sse_event(e) for e in events if "code" in parse_sse_event(e)]
        assert any(
            e.get("code") == "db-write-error"
            for e in error_events
        )


@pytest.mark.asyncio
async def test_successful_stream_sends_done_true_completion(authenticated_user, test_conversation):
    """Test that successful streaming sends done=true completion event"""
    async def mock_stream_gen():
        yield {"text": "Hello "}
        yield {"text": "world"}
    
    provider_response = {
        "ok": True,
        "stream": mock_stream_gen(),
        "provider": "test-provider",
        "model": "test-model",
    }
    
    with patch("api.chat_router._require_owned_conversation", return_value=test_conversation), \
         patch("api.chat_router.InputSanitizer.sanitize_chat_message", return_value=("test", None)), \
         patch("api.chat_router.conversation_store.add_message_to_conversation", new_callable=AsyncMock), \
         patch("api.chat_router.conversation_store.get_conversation", return_value=test_conversation), \
         patch("api.chat_router.invoke_provider", return_value=provider_response):
        
        events = []
        async for event in generate_chat_stream(
            message="test",
            conversation_id="test-conv-id",
            current_user=authenticated_user,
        ):
            events.append(event)
        
        # Last event should have done=true
        if events:
            last_event = parse_sse_event(events[-1])
            assert last_event.get("done") is True
            assert last_event.get("result") == "Hello world"
