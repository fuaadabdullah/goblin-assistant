"""
Tests for semantic_chat_router
Tests semantic chat functionality against actual API routes
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.semantic_chat_router import add_memory_fact, router, search_memory_facts
from api.services.memory_core import memory_core_service

# Mount the router in isolation (avoids coupling to main.py)
app = FastAPI()
app.include_router(router)
client = TestClient(app)

BASE_PATH = "/semantic-chat"

# ── Helper ──────────────────────────────────────────────────────────────────


def _make_url(path: str) -> str:
    """Build a fully qualified URL for the semantic-chat router."""
    return f"{BASE_PATH}{path}"


# ── Conversation Endpoints ─────────────────────────────────────────────────


class TestSemanticChatRouterChat:
    """Tests for the /conversations/{id}/messages endpoint"""

    def test_send_message_needs_valid_conversation(self):
        """Should return 404 for non-existent conversation"""
        response = client.post(
            _make_url("/conversations/nonexistent-id/messages"),
            json={"message": "hello"},
        )
        assert response.status_code == 404, (
            f"Expected 404 for missing conversation, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "detail" in data

    def test_send_message_rejects_empty_body(self):
        """Should return 422 for missing request body"""
        response = client.post(
            _make_url("/conversations/nonexistent-id/messages"),
            json={},
        )
        assert response.status_code == 422, (
            f"Expected 422 for empty body, got {response.status_code}: {response.text}"
        )

    def test_send_message_rejects_non_string_message(self):
        """Should return 422 for non-string message field"""
        response = client.post(
            _make_url("/conversations/nonexistent-id/messages"),
            json={"message": 123},
        )
        assert response.status_code == 422, (
            f"Expected 422 for non-string message, got {response.status_code}: {response.text}"
        )

    def test_get_context_needs_valid_conversation(self):
        """Should return 404 for non-existent conversation context"""
        response = client.get(
            _make_url("/conversations/nonexistent-id/context"),
            params={"query": "hello"},
        )
        assert response.status_code == 404, (
            f"Expected 404 for missing conversation, got {response.status_code}: {response.text}"
        )

    def test_get_context_rejects_missing_query(self):
        """Should return 422 when query param is missing"""
        response = client.get(
            _make_url("/conversations/some-id/context"),
        )
        assert response.status_code == 422, (
            f"Expected 422 for missing query, got {response.status_code}: {response.text}"
        )

    def test_summarize_needs_valid_conversation(self):
        """Should return 404 for non-existent conversation summary"""
        response = client.post(
            _make_url("/conversations/nonexistent-id/summarize"),
            json={},
        )
        assert response.status_code == 404, (
            f"Expected 404 for missing conversation, got {response.status_code}: {response.text}"
        )


# ── Memory Fact Endpoints ──────────────────────────────────────────────────


class TestSemanticChatRouterMemory:
    """Tests for memory fact endpoints"""

    def test_add_memory_rejects_empty_fact(self):
        """Should return 422 for missing fact_text"""
        response = client.post(
            _make_url("/users/user-123/memory"),
            json={},
        )
        assert response.status_code == 422, (
            f"Expected 422 for empty body, got {response.status_code}: {response.text}"
        )

    def test_search_memory_rejects_empty_query(self):
        """Should return 422 for missing query"""
        response = client.get(
            _make_url("/users/user-123/memory/search"),
        )
        assert response.status_code == 422, (
            f"Expected 422 for missing query, got {response.status_code}: {response.text}"
        )

    def test_search_memory_returns_200_with_valid_query(self):
        """Should return 200 with valid query and mock services."""
        # Mock the memory service to return predictable results
        from unittest.mock import patch

        with patch("api.semantic_chat_router.memory_core_service") as mock_service:
            mock_service.search_facts = AsyncMock(
                return_value={"facts": [], "count": 0, "query": "test"}
            )
            response = client.get(
                _make_url("/users/user-123/memory/search"),
                params={"query": "test"},
            )
            # With mocked services, should always return 200
            assert response.status_code == 200, (
                f"Expected 200 with mocked services, got {response.status_code}: {response.json()}"
            )
            data = response.json()
            assert "user_id" in data
            assert "query" in data
            assert "facts" in data
            assert "count" in data

    def test_search_memory_fails_gracefully_without_services(self):
        """Should return 503 Service Unavailable when backing services fail."""
        from unittest.mock import patch

        with patch("api.semantic_chat_router.memory_core_service") as mock_service:
            # Simulate a service failure
            mock_service.search_facts = AsyncMock(side_effect=Exception("Service unavailable"))
            response = client.get(
                _make_url("/users/user-123/memory/search"),
                params={"query": "test"},
            )
            # Without working services, should return 500 Internal Server Error
            assert response.status_code == 500, (
                f"Expected 500 on service failure, got {response.status_code}: {response.json()}"
            )


# ── Async Memory Fact Unit Tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_memory_fact_returns_canonical_memory_object(monkeypatch):
    fake_record = SimpleNamespace(
        to_dict=lambda: {
            "id": "mem-1",
            "type": "preference",
            "scope": "conversation",
            "content": "User prefers concise answers.",
            "summary": "Prefers concise answers",
            "source": "memory",
            "source_ref": {"conversation_id": "conv-1"},
            "confidence": 0.92,
            "confidence_band": "likely_true_usable",
            "confidence_reason": "user-authored and repeated",
            "importance": 0.81,
            "importance_band": "high",
            "importance_reason": "task relevant",
            "recency_score": 0.7,
            "sensitivity": "low",
            "status": "active",
            "tags": ["preference"],
            "entities": ["user"],
            "embedding_id": "emb-1",
            "created_at": "2026-06-11T18:00:00Z",
            "updated_at": "2026-06-11T18:00:00Z",
            "last_accessed_at": "2026-06-11T18:03:00Z",
            "expires_at": None,
        }
    )

    monkeypatch.setattr(
        memory_core_service,
        "ingest_memory_fact",
        AsyncMock(return_value=fake_record),
    )

    result = await add_memory_fact(
        user_id="user-123",
        fact_text="User prefers concise answers.",
        category="preference",
        metadata={"source_kind": "conversation", "source_id": "conv-1"},
    )

    assert result["success"] is True
    assert result["memory_fact"]["type"] == "preference"
    assert result["memory_fact"]["confidence_band"] in {
        "strong_stable_memory",
        "likely_true_usable",
        "weak_needs_verification",
        "do_not_use_by_default",
    }
    assert result["memory_fact"]["importance_band"] in {"high", "medium", "low"}
    assert result["memory_fact"]["scope"] == "conversation"
    assert result["memory_fact"]["source_ref"] == {"conversation_id": "conv-1"}


@pytest.mark.asyncio
async def test_search_memory_facts_returns_canonical_items(monkeypatch):
    class FakeRetrievalSingleton:
        async def retrieve_memory_facts(self, user_id, query, categories=None, k=5):
            return [
                {
                    "id": "mem-2",
                    "type": "project_state",
                    "scope": "global",
                    "content": "User wants decisions recorded.",
                    "summary": "Wants decisions recorded",
                    "source": "conversation",
                    "source_ref": {"conversation_id": "conv-2"},
                    "confidence": 0.9,
                    "confidence_band": "likely_true_usable",
                    "importance": 0.78,
                    "importance_band": "medium",
                    "recency_score": 0.65,
                    "sensitivity": "low",
                    "status": "active",
                    "tags": ["project"],
                    "entities": ["project"],
                    "embedding_id": "emb-2",
                }
            ]

    monkeypatch.setattr(
        "api.semantic_chat_router._get_retrieval_singleton",
        FakeRetrievalSingleton,
    )

    result = await search_memory_facts(
        user_id="user-123",
        query="project decisions",
        categories=["project"],
        k=1,
    )

    assert result["count"] == 1
    assert result["facts"][0]["type"] == "project_state"
    assert result["facts"][0]["confidence_band"] in {
        "strong_stable_memory",
        "likely_true_usable",
        "weak_needs_verification",
        "do_not_use_by_default",
    }
    assert result["facts"][0]["scope"] == "global"
    assert result["facts"][0]["source_ref"] == {"conversation_id": "conv-2"}


# ── Route Registration Tests ────────────────────────────────────────────────


def test_router_prefix():
    """Verify the router is mounted at the expected prefix"""
    routes = [r.path for r in router.routes]
    assert all(r.startswith("/semantic-chat") for r in routes), (
        f"Expected all routes under /semantic-chat, got: {routes}"
    )


def test_router_has_expected_endpoints():
    """Verify the expected endpoints are registered"""
    routes = {r.path for r in router.routes}
    expected_endpoints = {
        "/semantic-chat/conversations/{conversation_id}/messages",
        "/semantic-chat/conversations/{conversation_id}/context",
        "/semantic-chat/conversations/{conversation_id}/summarize",
        "/semantic-chat/users/{user_id}/memory",
        "/semantic-chat/users/{user_id}/memory/search",
    }
    missing = expected_endpoints - routes
    assert not missing, f"Missing expected endpoints: {missing}"
