"""Tests for api.api_keys_router."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import api_keys_router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(api_keys_router.router, prefix="/api/v1")
    return TestClient(app)


def test_store_get_and_delete_api_key_round_trip(tmp_path, monkeypatch):
    keys_file = tmp_path / "api_keys.json"
    monkeypatch.setattr(api_keys_router, "API_KEYS_FILE", str(keys_file))
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
    assert json.loads(Path(keys_file).read_text(encoding="utf-8")) == {}


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
