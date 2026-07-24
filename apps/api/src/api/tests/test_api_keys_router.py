"""Tests for api.routes.api_keys_router."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import api_keys_router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(api_keys_router.router, prefix="/api/v1")
    return TestClient(app)


class _FakeStore:
    def __init__(self):
        self.keys = {}

    async def get(self, provider: str):
        return self.keys.get(provider)

    async def set(self, provider: str, key: str):
        self.keys[provider] = key

    async def delete(self, provider: str):
        self.keys.pop(provider, None)


def test_store_get_and_delete_api_key_round_trip(tmp_path, monkeypatch):
    keys_file = tmp_path / "api_keys.json"
    monkeypatch.setattr(api_keys_router, "API_KEYS_FILE", str(keys_file))
    fake_store = _FakeStore()
    monkeypatch.setattr(api_keys_router, "create_api_key_store", lambda: fake_store)
    client = _client()

    stored = client.post("/api/v1/api-keys/openai", json={"key": "secret-123"})
    fetched = client.get("/api/v1/api-keys/openai")
    deleted = client.delete("/api/v1/api-keys/openai")
    missing = client.get("/api/v1/api-keys/openai")

    assert stored.status_code == 200
    assert stored.json()["message"] == "API key stored for openai"

    assert fetched.status_code == 200
    assert fetched.json() == {"key": "secret-123", "provider": "openai"}

    assert deleted.status_code == 200
    assert deleted.json()["message"] == "API key deleted for openai"

    assert missing.status_code == 200
    assert missing.json() == {"key": None, "provider": "openai"}
    assert fake_store.keys == {}


def test_store_api_key_failure_preserves_message(tmp_path, monkeypatch):
    keys_file = tmp_path / "api_keys.json"
    monkeypatch.setattr(api_keys_router, "API_KEYS_FILE", str(keys_file))
    monkeypatch.setattr(
        api_keys_router,
        "create_api_key_store",
        lambda: MagicMock(set=AsyncMock(side_effect=RuntimeError("disk full"))),
    )
    monkeypatch.setattr(
        api_keys_router,
        "load_api_keys_async",
        AsyncMock(return_value={}),
    )
    client = _client()

    response = client.post("/api/v1/api-keys/openai", json={"key": "secret-123"})

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to store API key: disk full"


def test_load_api_keys_handles_missing_and_invalid_files(
    tmp_path,
    monkeypatch,
):
    keys_file = tmp_path / "api_keys.json"
    monkeypatch.setattr(api_keys_router, "API_KEYS_FILE", str(keys_file))

    assert api_keys_router.load_api_keys() == {}

    keys_file.write_text("not-json", encoding="utf-8")
    assert api_keys_router.load_api_keys() == {}


def test_save_api_keys_writes_indented_json(tmp_path, monkeypatch):
    keys_file = tmp_path / "api_keys.json"
    monkeypatch.setattr(api_keys_router, "API_KEYS_FILE", str(keys_file))

    api_keys_router.save_api_keys({"openai": "secret-123"})

    assert keys_file.exists()
    assert keys_file.read_text(encoding="utf-8").strip().startswith("{")
    assert json.loads(keys_file.read_text(encoding="utf-8")) == {"openai": "secret-123"}
