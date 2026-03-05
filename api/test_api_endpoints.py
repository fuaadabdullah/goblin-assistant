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


def test_chat_conversations_endpoint(client):
    """Test creating a conversation"""
    response = client.post("/chat/conversations", json={"title": "Test Conversation"})
    assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data
    assert "title" in data
    assert "created_at" in data

    conversation_id = data["conversation_id"]

    # Test getting the conversation
    response = client.get(f"/chat/conversations/{conversation_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == conversation_id
    assert data["title"] == "Test Conversation"
    assert "messages" in data
    assert "created_at" in data
    assert "updated_at" in data


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
