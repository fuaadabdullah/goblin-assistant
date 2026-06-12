"""Critical API contract boundary tests.

These tests pin response shape and status behavior for Tier 0 paths.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import api_router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(api_router.router)
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
            "/api/chat",
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
    response = client.post("/api/generate", json={"model": "gpt-4o-mini"})

    assert response.status_code == CRITICAL_STATUS_TABLE["generate_missing_prompt"]
    payload = response.json()
    assert "detail" in payload
    assert isinstance(payload["detail"], str)
    assert "Either 'messages' or 'prompt' must be provided" in payload["detail"]


def test_contract_stream_poll_missing_shape():
    client = _client()
    response = client.get("/api/route_task_stream_poll/non-existent")

    assert response.status_code == CRITICAL_STATUS_TABLE["stream_missing"]
    payload = response.json()
    assert payload == {"detail": "Stream not found"}
