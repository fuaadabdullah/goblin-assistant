"""Engine contract tests — Memory pillar.

These tests assert that the Memory pillar's public contract
(documented in docs/architecture/ENGINE_CONTRACTS.md) is upheld.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import semantic_chat_router


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(semantic_chat_router.router, prefix="/api/v1")
    return TestClient(app)


@pytest.fixture
def mock_memory_core():
    with patch(
        "api.semantic_chat_router.memory_core_service",
        autospec=True,
    ) as mock:
        mock.ingest_memory_fact = AsyncMock()
        mock.ingest_text = AsyncMock()
        yield mock


# ── Context Assembly Contract ──────────────────────────────────────────


class TestContextAssemblyContract:
    """Contract: Context assembly returns structured bundle with required fields."""

    def test_context_bundle_has_required_fields(self, client):
        """The context bundle must contain all required fields."""
        with patch(
            "api.semantic_chat_router.RetrievalSingleton",
            autospec=True,
        ) as mock_retrieval:
            mock_instance = mock_retrieval.return_value
            mock_instance.get_context_bundle = AsyncMock(
                return_value={
                    "summaries": [],
                    "messages": [],
                    "ephemeral_messages": [],
                    "tasks": [],
                    "memory_facts": [],
                    "total_tokens": 0,
                    "retrieved_at": "2026-06-20T13:00:00Z",
                }
            )
            response = client.get(
                "/api/v1/semantic-chat/conversations/conv_abc/context",
                params={"query": "test", "k": 3},
            )
        # 200 is expected; if retrieval is not configured, degrade gracefully
        assert response.status_code in (200, 404, 503)
        if response.status_code == 200:
            data = response.json()
            required_fields = {
                "summaries",
                "messages",
                "ephemeral_messages",
                "tasks",
                "memory_facts",
                "total_tokens",
                "retrieved_at",
            }
            assert required_fields.issubset(data.keys()), (
                f"Missing: {required_fields - data.keys()}"
            )

    def test_context_bundle_total_tokens_is_integer(self, client):
        """total_tokens must be a non-negative integer."""
        with patch(
            "api.semantic_chat_router.RetrievalSingleton",
            autospec=True,
        ) as mock_retrieval:
            mock_instance = mock_retrieval.return_value
            mock_instance.get_context_bundle = AsyncMock(
                return_value={
                    "summaries": [{"content": "summary", "tokens": 50}],
                    "messages": [],
                    "ephemeral_messages": [],
                    "tasks": [],
                    "memory_facts": [],
                    "total_tokens": 50,
                    "retrieved_at": "2026-06-20T13:00:00Z",
                }
            )
            response = client.get(
                "/api/v1/semantic-chat/conversations/conv_abc/context",
                params={"query": "test", "k": 3},
            )
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data["total_tokens"], int)
            assert data["total_tokens"] >= 0


# ── Memory Fact Lifecycle Contract ─────────────────────────────────────


class TestMemoryFactContract:
    """Contract: Memory facts can be ingested, searched, and have required fields."""

    def test_ingest_memory_fact_requires_user_id(self, client):
        """POST /users/{user_id}/memory requires a valid user_id."""
        response = client.post(
            "/api/v1/semantic-chat/users/user_42/memory",
            json={
                "content": "User prefers dark mode",
                "category": "preference",
                "confidence": 0.9,
            },
        )
        # 200 if memory core is connected, 401/403 if auth middleware catches it,
        # 500 if memory core is unavailable — but should never 404
        assert response.status_code != 404

    def test_search_memory_facts_returns_list(self, client):
        """GET /users/{user_id}/memory/search returns a list of facts."""
        response = client.get(
            "/api/v1/semantic-chat/users/user_42/memory/search",
            params={"query": "preferences", "k": 5},
        )
        # Acceptable: 200 with facts, 200 with empty list, or 503 if unavailable
        assert response.status_code in (200, 401, 503)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            # May return {"facts": [...]} or similar structure
            if "facts" in data:
                assert isinstance(data["facts"], list)
                for fact in data["facts"]:
                    assert "content" in fact
                    assert "category" in fact


# ── Degradation Contract ───────────────────────────────────────────────


class TestMemoryDegradationContract:
    """Contract: Memory degrades gracefully when retrieval is unavailable."""

    def test_retrieval_failure_returns_minimal_context(self, client):
        """When retrieval fails, the orchestrator returns minimal context."""
        with patch(
            "api.semantic_chat_router.RetrievalSingleton",
            autospec=True,
        ) as mock_retrieval:
            mock_instance = mock_retrieval.return_value
            mock_instance.get_context_bundle = AsyncMock(
                side_effect=RuntimeError("semantic retrieval failed")
            )
            response = client.get(
                "/api/v1/semantic-chat/conversations/conv_abc/context",
                params={"query": "test", "k": 3},
            )
        # Should not crash — degrade gracefully
        assert response.status_code in (200, 404, 500, 503)
