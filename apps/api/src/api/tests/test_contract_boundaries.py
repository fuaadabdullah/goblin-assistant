"""Critical API contract boundary tests.

These tests pin response shape and status behavior for Tier 0 paths.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import api_router
from api.services.goblin_query_service import build_goblin_query_service


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(api_router.router, prefix="/api/v1")
    return TestClient(app)


def _goblin_client() -> TestClient:
    app = FastAPI()
    app.include_router(api_router.router, prefix="/api/v1")

    class _EmptyRepo:
        async def list_history(self, *, user_id, goblin_id, scan_limit):
            return []

        async def get_stats(self, *, user_id, goblin_id, started_at, ended_at):
            del user_id, goblin_id, started_at, ended_at
            return {
                "total_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "success_rate": None,
                "average_duration_ms": None,
                "p95_duration_ms": None,
                "total_cost": None,
            }

    service = build_goblin_query_service(user_id="u1", history_repository=_EmptyRepo())
    app.dependency_overrides[api_router.get_goblin_query_service] = lambda: service
    return TestClient(app)


CRITICAL_STATUS_TABLE = {
    "chat_success": 200,
    "generate_missing_prompt": 400,
    "stream_missing": 404,
}


def test_contract_chat_success_shape():
    client = _client()
    with patch(
        "api.api_router.invoke_provider",
        new_callable=AsyncMock,
        return_value={
            "ok": True,
            "result": {"text": "hello"},
            "provider": "openai",
            "model": "gpt-4o-mini",
        },
    ):
        response = client.post(
            "/api/v1/api/chat",
            json={"messages": [{"role": "user", "content": "ping"}]},
        )

    assert response.status_code == CRITICAL_STATUS_TABLE["chat_success"]
    payload = response.json()
    assert set(["ok", "result", "provider", "model"]).issubset(payload.keys())
    assert payload["ok"] is True
    assert isinstance(payload["result"], dict)
    assert isinstance(payload["result"]["text"], str)


def test_contract_generate_validation_shape():
    client = _client()
    response = client.post("/api/v1/api/generate", json={"model": "gpt-4o-mini"})

    assert response.status_code == CRITICAL_STATUS_TABLE["generate_missing_prompt"]
    payload = response.json()
    assert "detail" in payload
    assert isinstance(payload["detail"], str)
    assert "Either 'messages' or 'prompt' must be provided" in payload["detail"]


def test_contract_stream_poll_missing_shape():
    client = _client()
    response = client.get("/api/v1/api/route_task_stream_poll/non-existent")

    assert response.status_code == CRITICAL_STATUS_TABLE["stream_missing"]
    payload = response.json()
    assert payload == {"detail": "Stream not found"}


def test_contract_goblins_list_shape():
    client = _goblin_client()
    response = client.get("/api/v1/api/goblins")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    data = payload["data"]
    assert {"items", "total", "limit", "order"}.issubset(data.keys())
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)
    assert data["limit"] == 100
    assert "501" not in str(response.status_code)
    for item in data["items"]:
        assert {"id", "name", "status", "active"}.issubset(item.keys())
        assert "provider" not in item


def test_contract_goblin_history_shape():
    client = _goblin_client()
    response = client.get("/api/v1/api/history/coding")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    data = payload["data"]
    assert {"items", "total", "limit", "order"}.issubset(data.keys())
    assert isinstance(data["items"], list)
    assert data["order"] == "newest_first"


def test_contract_goblin_stats_shape():
    client = _goblin_client()
    response = client.get("/api/v1/api/stats/coding")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    data = payload["data"]
    assert {"goblin_id", "window", "counters"}.issubset(data.keys())
    assert data["goblin_id"] == "coding"
    assert {"hours", "started_at", "ended_at"}.issubset(data["window"].keys())
    assert {"total_tasks", "completed_tasks", "failed_tasks"}.issubset(data["counters"].keys())
