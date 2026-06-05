"""
Real integration tests for the chat completion pipeline.

Uses the full app + real auth + InMemoryConversationStore.
Only _cr.invoke_provider is intercepted — everything else is real:
- Input sanitization (XSS stripping)
- Conversation ownership enforcement
- Message persistence via real conversation store
- Response shape assembly

The unit tests mock all of the above and assert on pre-baked values.
"""

import pytest
from unittest.mock import patch, AsyncMock

pytestmark = pytest.mark.asyncio

_MOCK_RESPONSE = "Integration test LLM response."


def _make_mock_invoke(text=_MOCK_RESPONSE):
    """Patch target: api.chat_router.invoke_provider (the _cr attribute)."""

    async def _fake_invoke(pid, model, payload, **kwargs):
        return {
            "ok": True,
            "text": text,
            "provider": pid or "mock",
            "model": model or "mock-gpt",
            "result": {"text": text},
            "latency_ms": 5.0,
            "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
        }

    return patch("api.chat_router.invoke_provider", side_effect=_fake_invoke)


async def _get_csrf(client):
    r = await client.get("/v1/auth/csrf-token")
    assert r.status_code == 200
    return r.json()["data"]["csrf_token"]


async def _register(client, email, password="TestPass123!"):
    csrf = await _get_csrf(client)
    r = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "csrf_token": csrf},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]


class TestSendMessage:
    async def test_send_message_response_shape(self, client, auth_headers, conversation):
        """The response must contain all required fields with correct types."""
        conv_id = conversation["conversation_id"]
        with _make_mock_invoke():
            r = await client.post(
                f"/v1/chat/conversations/{conv_id}/messages",
                json={"message": "Hello integration test", "provider": "mock"},
                headers=auth_headers,
            )
        assert r.status_code == 200, r.text
        data = r.json()["data"]

        assert data["message_id"], "message_id must be non-empty"
        assert data["response"] == _MOCK_RESPONSE
        assert data["provider"]  # non-null string
        assert data["timestamp"]  # ISO 8601 parseable

        # Verify timestamp is parseable
        from datetime import datetime
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

    async def test_send_message_round_trip_via_api(self, client, auth_headers, conversation):
        """
        After sending, GET /conversations/{id} must return both the user
        message and the assistant reply. This proves persistence runs real
        through the InMemoryConversationStore.
        """
        conv_id = conversation["conversation_id"]
        with _make_mock_invoke():
            await client.post(
                f"/v1/chat/conversations/{conv_id}/messages",
                json={"message": "What is 2+2?", "provider": "mock"},
                headers=auth_headers,
            )

        r = await client.get(f"/v1/chat/conversations/{conv_id}", headers=auth_headers)
        assert r.status_code == 200, r.text
        messages = r.json()["data"]["messages"]

        assert len(messages) >= 2, f"Expected ≥2 messages, got {len(messages)}"

        roles = [m["role"] for m in messages]
        assert "user" in roles, "User message not persisted"
        assert "assistant" in roles, "Assistant message not persisted"

        user_msgs = [m for m in messages if m["role"] == "user"]
        assert user_msgs[0]["content"] == "What is 2+2?"

        asst_msgs = [m for m in messages if m["role"] == "assistant"]
        assert asst_msgs[0]["content"] == _MOCK_RESPONSE

    async def test_send_message_unauthenticated_returns_401(self, client, auth_headers, conversation):
        """Missing auth header must 401."""
        conv_id = conversation["conversation_id"]
        r = await client.post(
            f"/v1/chat/conversations/{conv_id}/messages",
            json={"message": "test"},
        )
        assert r.status_code == 401

    async def test_send_message_wrong_owner_returns_4xx(self, client, auth_headers, conversation):
        """
        User B must not be able to send to user A's conversation.
        Exercises the real _require_owned_conversation ownership check.
        """
        # Register a second user and log them in
        user_b_data = await _register(client, "user-b@test.example")
        b_headers = {"Authorization": f"Bearer {user_b_data['access_token']}"}

        conv_id = conversation["conversation_id"]
        with _make_mock_invoke():
            r = await client.post(
                f"/v1/chat/conversations/{conv_id}/messages",
                json={"message": "I should not see this", "provider": "mock"},
                headers=b_headers,
            )
        assert r.status_code in (403, 404), (
            f"Expected 403 or 404 for wrong owner, got {r.status_code}: {r.text}"
        )

    async def test_xss_input_is_sanitized(self, client, auth_headers, conversation):
        """
        InputSanitizer.sanitize_chat_message() must strip script tags.
        The round-trip API check proves sanitization ran against the real
        store, not a mock.
        """
        conv_id = conversation["conversation_id"]
        xss_payload = '<script>alert("xss")</script>Hello'

        with _make_mock_invoke():
            r = await client.post(
                f"/v1/chat/conversations/{conv_id}/messages",
                json={"message": xss_payload, "provider": "mock"},
                headers=auth_headers,
            )
        assert r.status_code == 200, r.text

        # Retrieve the conversation and check the stored user message
        conv_r = await client.get(f"/v1/chat/conversations/{conv_id}", headers=auth_headers)
        messages = conv_r.json()["data"]["messages"]
        user_msgs = [m for m in messages if m["role"] == "user"]
        assert user_msgs, "User message not found in conversation"

        stored_content = user_msgs[0]["content"]
        assert "<script>" not in stored_content, (
            f"<script> tag survived sanitization. Stored: {stored_content!r}"
        )

    async def test_context_assembly_does_not_crash_on_empty_history(
        self, client, auth_headers, conversation
    ):
        """enable_context_assembly=true on a fresh conversation must not 500."""
        conv_id = conversation["conversation_id"]
        with _make_mock_invoke():
            r = await client.post(
                f"/v1/chat/conversations/{conv_id}/messages",
                json={
                    "message": "Summarize our conversation history",
                    "provider": "mock",
                    "enable_context_assembly": True,
                },
                headers=auth_headers,
            )
        assert r.status_code == 200, f"Context assembly crashed: {r.text}"


class TestConversationManagement:
    async def test_create_conversation_returns_conversation_id(self, client, auth_headers):
        r = await client.post(
            "/v1/chat/conversations",
            json={"title": "New Conversation"},
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["conversation_id"]
        assert data["title"] == "New Conversation"

    async def test_list_conversations_includes_created_conversation(
        self, client, auth_headers, conversation
    ):
        r = await client.get("/v1/chat/conversations", headers=auth_headers)
        assert r.status_code == 200, r.text
        conv_ids = [c["conversation_id"] for c in r.json()["data"]]
        assert conversation["conversation_id"] in conv_ids

    async def test_get_conversation_returns_messages(self, client, auth_headers, conversation):
        conv_id = conversation["conversation_id"]
        with _make_mock_invoke():
            await client.post(
                f"/v1/chat/conversations/{conv_id}/messages",
                json={"message": "test message", "provider": "mock"},
                headers=auth_headers,
            )
        r = await client.get(f"/v1/chat/conversations/{conv_id}", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert "messages" in data
        assert len(data["messages"]) >= 2
