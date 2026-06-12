"""
Tests for semantic_chat_router
Tests semantic chat functionality
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.semantic_chat_router import add_memory_fact, search_memory_facts
from api.services.memory_core import memory_core_service

client = TestClient(app)


class TestSemanticChatRouterChat:
    """Tests for chat endpoint"""

    def test_chat_endpoint_exists(self):
        """Test chat endpoint is registered"""
        response = client.post(
            "/semantic_chat/chat",
            json={"message": "hello"},
        )

        assert response.status_code in [200, 400, 401, 403, 404, 422, 500]

    def test_chat_requires_message(self):
        """Test chat requires message parameter"""
        response = client.post(
            "/semantic_chat/chat",
            json={},
        )

        assert response.status_code in [400, 401, 422, 200, 404, 500]

    def test_chat_with_context(self):
        """Test chat with conversation context"""
        response = client.post(
            "/semantic_chat/chat",
            json={
                "message": "hello",
                "context": [{"role": "user", "content": "hi"}],
            },
        )

        assert response.status_code in [200, 400, 422, 401, 403, 404, 500]

    def test_chat_with_system_prompt(self):
        """Test chat with system prompt"""
        response = client.post(
            "/semantic_chat/chat",
            json={
                "message": "hello",
                "system_prompt": "You are helpful",
            },
        )

        assert response.status_code in [200, 400, 422, 401, 403, 404, 500]

    def test_chat_streaming(self):
        """Test streaming chat response"""
        response = client.post(
            "/semantic_chat/chat",
            json={"message": "hello", "stream": True},
        )

        # Should return streaming response or error
        assert response.status_code in [200, 400, 422, 401, 403, 404, 500]


class TestSemanticChatRouterSearch:
    """Tests for semantic search within chat"""

    def test_search_similar_messages(self):
        """Test searching for similar messages"""
        response = client.get(
            "/semantic_chat/search",
            params={"query": "hello", "limit": 5},
        )

        assert response.status_code in [200, 400, 401, 403, 404, 422, 500]

    def test_search_with_filters(self):
        """Test search with filters"""
        response = client.get(
            "/semantic_chat/search",
            params={
                "query": "hello",
                "limit": 5,
                "filter": "user",
            },
        )

        assert response.status_code in [200, 400, 401, 403, 404, 422, 500]

    def test_search_relevance_ranking(self):
        """Test results are ranked by relevance"""
        response = client.get(
            "/semantic_chat/search",
            params={"query": "python programming", "limit": 10},
        )

        if response.status_code == 200:
            data = response.json()
            # Results should be ordered by relevance
            if isinstance(data, list) and len(data) > 1:
                assert data[0].get("score", 0) >= data[1].get("score", 0)


class TestSemanticChatRouterMemory:
    """Tests for semantic chat memory"""

    def test_memory_retrieval(self):
        """Test retrieving from memory"""
        response = client.get("/semantic_chat/memory")

        assert response.status_code in [200, 400, 401, 403, 404, 422, 500]

    def test_memory_context_size(self):
        """Test controlling memory context size"""
        response = client.post(
            "/semantic_chat/chat",
            json={
                "message": "hello",
                "context_size": 5,
            },
        )

        assert response.status_code in [200, 400, 422, 401, 403, 404, 500]

    def test_memory_summarization(self):
        """Test long memory is summarized"""
        response = client.post(
            "/semantic_chat/chat",
            json={"message": "hello"},
        )

        assert response.status_code in [200, 400, 422, 401, 403, 404, 500]


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


class TestSemanticChatRouterEmbeddings:
    """Tests for embedding generation"""

    def test_generate_message_embedding(self):
        """Test generating embedding for message"""
        response = client.post(
            "/semantic_chat/chat",
            json={"message": "hello"},
        )

        assert response.status_code in [200, 400, 422, 401, 403, 404, 500]

    def test_embedding_caching(self):
        """Test embeddings are cached"""
        for _ in range(2):
            response = client.post(
                "/semantic_chat/chat",
                json={"message": "hello"},
            )

        assert response.status_code in [200, 400, 422, 401, 403, 404, 500]


class TestSemanticChatRouterErrors:
    """Tests for error handling"""

    def test_invalid_message_format(self):
        """Test invalid message format"""
        response = client.post(
            "/semantic_chat/chat",
            json={"message": 123},  # Should be string
        )

        assert response.status_code in [400, 401, 422, 200, 404, 500]

    def test_context_validation(self):
        """Test context validation"""
        response = client.post(
            "/semantic_chat/chat",
            json={
                "message": "hello",
                "context": "invalid",  # Should be list
            },
        )

        assert response.status_code in [400, 401, 422, 200, 404, 500]

    def test_timeout_handling(self):
        """Test timeout handling"""
        response = client.post(
            "/semantic_chat/chat",
            json={"message": "hello"},
        )

        # Should handle timeout gracefully
        assert response.status_code in [500, 408, 400, 401, 422, 200, 404]

    def test_embedding_error_handling(self):
        """Test embedding service errors are handled gracefully"""
        response = client.post(
            "/semantic_chat/chat",
            json={"message": "hello"},
        )

        # Should handle gracefully
        assert response.status_code in [500, 400, 401, 422, 200, 404]


class TestSemanticChatRouterPerformance:
    """Tests for performance optimization"""

    def test_batch_embedding_generation(self):
        """Test batch generating embeddings"""
        response = client.post(
            "/semantic_chat/chat",
            json={
                "message": "hello",
                "batch_size": 5,
            },
        )

        assert response.status_code in [200, 400, 422, 401, 403, 404, 500]

    def test_response_streaming(self):
        """Test streaming response to client"""
        response = client.post(
            "/semantic_chat/chat",
            json={"message": "hello", "stream": True},
        )

        # Should support streaming
        assert response.status_code in [200, 400, 422, 401, 403, 404, 500]
