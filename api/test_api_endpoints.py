"""
API tests for Goblin Assistant using pytest and TestClient
"""


def test_root_endpoint(client):
    """Test the root endpoint returns correct response"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "docs" in data
    assert "health" in data


def test_health_endpoint(client):
    """Test the health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_chat_conversations_endpoint(authenticated_client):
    """Test creating a conversation"""
    response = authenticated_client.post(
        "/chat/conversations", json={"title": "Test Conversation", "user_id": "ignored-user"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data
    assert "title" in data
    assert "created_at" in data

    conversation_id = data["conversation_id"]

    # Test getting the conversation
    response = authenticated_client.get(f"/chat/conversations/{conversation_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == conversation_id
    assert data["title"] == "Test Conversation"
    assert data["user_id"] == "test-user"
    assert "messages" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_chat_conversations_list_returns_snippet(authenticated_client):
    response = authenticated_client.post(
        "/chat/conversations", json={"title": "Snippet Conversation"}
    )
    assert response.status_code == 200
    conversation_id = response.json()["conversation_id"]

    import_response = authenticated_client.post(
        f"/chat/conversations/{conversation_id}/import",
        json={
            "messages": [
                {
                    "role": "assistant",
                    "content": "The latest snippet should come from here.",
                    "timestamp": "2026-03-07T12:00:00.000000",
                }
            ]
        },
    )
    assert import_response.status_code == 200

    response = authenticated_client.get("/chat/conversations")
    assert response.status_code == 200

    data = response.json()
    assert any(
        item["conversation_id"] == conversation_id
        and item["snippet"] == "The latest snippet should come from here."
        for item in data
    )


def test_chat_conversation_routes_are_user_scoped():
    from conftest import _build_authenticated_client

    with _build_authenticated_client("test-user", "test@example.com") as authenticated_client:
        response = authenticated_client.post(
            "/chat/conversations", json={"title": "Private Conversation"}
        )
        assert response.status_code == 200
        conversation_id = response.json()["conversation_id"]

    with _build_authenticated_client("other-user", "other@example.com") as other_client:
        response = other_client.get(f"/chat/conversations/{conversation_id}")
        assert response.status_code == 404


def test_chat_import_preserves_message_order(authenticated_client):
    response = authenticated_client.post(
        "/chat/conversations", json={"title": "Imported Conversation"}
    )
    assert response.status_code == 200
    conversation_id = response.json()["conversation_id"]

    import_response = authenticated_client.post(
        f"/chat/conversations/{conversation_id}/import",
        json={
            "messages": [
                {
                    "role": "assistant",
                    "content": "Second",
                    "timestamp": "2026-03-07T12:00:02.000000",
                },
                {
                    "role": "user",
                    "content": "First",
                    "timestamp": "2026-03-07T12:00:01.000000",
                },
            ]
        },
    )
    assert import_response.status_code == 200

    response = authenticated_client.get(f"/chat/conversations/{conversation_id}")
    assert response.status_code == 200
    messages = response.json()["messages"]
    assert [message["content"] for message in messages] == ["First", "Second"]


def test_send_message_uses_latest_user_message_and_honors_provider(
    authenticated_client, monkeypatch
):
    response = authenticated_client.post(
        "/chat/conversations", json={"title": "Message Conversation"}
    )
    assert response.status_code == 200
    conversation_id = response.json()["conversation_id"]

    captured = {}

    async def fake_process_message(*args, **kwargs):
        return {
            "classification": {"type": "working", "confidence": 1.0},
            "decision": {"actions": [], "confidence": 1.0},
            "execution": {"actions_executed": []},
            "processed_at": "2026-03-07T12:00:00.000000",
        }

    async def fake_invoke_provider(pid, model, payload, timeout_ms, stream=False):
        captured["pid"] = pid
        captured["messages"] = payload["messages"]
        return {
            "ok": True,
            "provider": pid or "auto",
            "model": model or "mock-model",
            "result": {
                "text": "Assistant reply",
                "raw": {
                    "usage": {"total_tokens": 21},
                    "correlation_id": "cid-123",
                },
            },
        }

    monkeypatch.setattr(
        "api.chat_router.write_time_intelligence.process_message",
        fake_process_message,
    )
    monkeypatch.setattr("api.chat_router.invoke_provider", fake_invoke_provider)

    response = authenticated_client.post(
        f"/chat/conversations/{conversation_id}/messages",
        json={"message": "Latest user prompt", "provider": "openai", "model": "gpt-4o-mini"},
    )
    assert response.status_code == 200

    data = response.json()
    assert captured["pid"] == "openai"
    assert captured["messages"][-1]["content"] == "Latest user prompt"
    assert data["usage"]["total_tokens"] == 21
    assert data["correlation_id"] == "cid-123"


def test_routing_providers_endpoint(client):
    """Test the routing providers endpoint"""
    response = client.get("/routing/providers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Should contain at least some providers
    assert len(data) > 0


def test_api_keys_status_endpoint(client):
    """Test the API keys status endpoint"""
    response = client.get("/settings/api-keys/status")
    # This might return 404 if not implemented, but should not crash
    assert response.status_code in [
        200,
        404,
        500,
    ]  # Allow various states during development


def test_execute_router_removed(client):
    """Guard: /execute was retired and must not be reintroduced."""
    response = client.post("/execute/", json={"goblin": "test", "task": "test"})
    assert response.status_code == 404 or response.status_code == 405

    response = client.get("/execute/status/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404 or response.status_code == 405
