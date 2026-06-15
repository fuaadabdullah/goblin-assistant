"""Contract tests for the current api.search_router behavior."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth.router import User, get_current_user
from api.search_router import router


@asynccontextmanager
async def _empty_db():
    class _Result:
        def fetchall(self):
            return []

    class _Session:
        async def execute(self, *_args, **_kwargs):
            return _Result()

    yield _Session()


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: User(
        id="u-1",
        email="test@example.com",
    )
    return TestClient(app)


def test_query_returns_empty_when_embedding_is_empty() -> None:
    client = _client()

    with patch("api.services.embedding_service.EmbeddingService") as svc_cls:
        svc = svc_cls.return_value
        svc.embed_text = AsyncMock(return_value=[])
        response = client.post("/api/v1/search/query", json={"query": "python"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["results"] == []
    assert payload["data"]["total_results"] == 0


def test_query_merges_and_limits_ranked_results() -> None:
    client = _client()

    with (
        patch("api.services.embedding_service.EmbeddingService") as svc_cls,
        patch("api.search_router.retrieve_by_source_type", new=AsyncMock()) as retrieve,
    ):
        svc = svc_cls.return_value
        svc.embed_text = AsyncMock(return_value=[0.1, 0.2])
        retrieve.side_effect = [
            [
                {
                    "id": "a",
                    "content": "python intro",
                    "source_type": "document",
                    "source_id": "d1",
                    "metadata": {"tag": "x"},
                    "score": 0.8,
                }
            ],
            [
                {
                    "id": "b",
                    "content": "python async",
                    "source_type": "code",
                    "source_id": "c1",
                    "metadata": None,
                    "score": 0.95,
                }
            ],
        ]

        response = client.post(
            "/api/v1/search/query",
            json={"query": "python", "source_types": ["document", "code"], "k": 1},
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_results"] == 1
    assert data["results"][0]["id"] == "b"


def test_list_collections_returns_success_envelope() -> None:
    client = _client()

    with patch("api.search_router.get_db", _empty_db):
        response = client.get("/api/v1/search/collections")

    assert response.status_code == 200
    assert response.json()["data"]["collections"] == []
