"""Tests for POST /ops/colab-worker/register and dispatcher.update_provider_endpoint."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

_API_KEY = "test-colab-api-key"
_TUNNEL_URL = "https://abc123.trycloudflare.com"


# ---------------------------------------------------------------------------
# dispatcher.update_provider_endpoint
# ---------------------------------------------------------------------------


def _make_dispatcher(endpoint_env: str = "COLAB_WORKER_ENDPOINT"):
    from api.providers.dispatcher import ProviderDispatcher

    configs = {
        "colab_worker": {
            "endpoint": "",
            "endpoint_env": endpoint_env,
            "api_key_env": "COLAB_WORKER_API_KEY",
            "default_model": "gemma-3-12b",
        }
    }
    from api.providers.mock_provider import MockProvider

    return ProviderDispatcher(configs=configs, class_map={"colab_worker": MockProvider})


def test_update_provider_endpoint_patches_config():
    dispatcher = _make_dispatcher()
    dispatcher.update_provider_endpoint("colab_worker", _TUNNEL_URL)

    assert dispatcher._configs["colab_worker"]["endpoint"] == _TUNNEL_URL


def test_update_provider_endpoint_patches_env_var():
    dispatcher = _make_dispatcher()
    dispatcher.update_provider_endpoint("colab_worker", _TUNNEL_URL)

    assert os.environ.get("COLAB_WORKER_ENDPOINT") == _TUNNEL_URL


def test_update_provider_endpoint_evicts_cached_instance():
    dispatcher = _make_dispatcher()
    # Seed a fake cached instance
    dispatcher._providers["colab_worker"] = MagicMock()
    dispatcher.update_provider_endpoint("colab_worker", _TUNNEL_URL)

    assert "colab_worker" not in dispatcher._providers


def test_update_provider_endpoint_clears_list_cache():
    dispatcher = _make_dispatcher()
    dispatcher._provider_list_cache[False] = [{"id": "colab_worker"}]
    dispatcher.update_provider_endpoint("colab_worker", _TUNNEL_URL)

    assert dispatcher._provider_list_cache == {}


def test_update_provider_endpoint_unknown_provider_raises():
    dispatcher = _make_dispatcher()
    with pytest.raises(KeyError):
        dispatcher.update_provider_endpoint("nonexistent", _TUNNEL_URL)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app():
    from fastapi import FastAPI
    from api.ops_routes.colab_worker import router

    app = FastAPI()
    app.include_router(router)
    return app


def _client(env_overrides: dict[str, str] | None = None):
    overrides = {"COLAB_WORKER_API_KEY": _API_KEY, "ENVIRONMENT": "development"}
    if env_overrides:
        overrides.update(env_overrides)
    with patch.dict(os.environ, overrides):
        return TestClient(_make_app())


def _mock_health_ok():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"healthy": True}
    return mock_resp


def _mock_health_status(status_code: int):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {}
    return mock_resp


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------


def test_register_endpoint_success():
    with (
        patch("api.ops_routes.colab_worker._probe_health", new=AsyncMock(return_value={"healthy": True})),
        patch("api.providers.dispatcher.dispatcher.update_provider_endpoint"),
        patch("api.services.provider_health.health_monitor.probe_provider", new=AsyncMock()),
        patch.dict(os.environ, {"COLAB_WORKER_API_KEY": _API_KEY, "ENVIRONMENT": "development"}),
        patch("api.ops_routes.colab_worker._write_env_file", return_value=True),
    ):
        from fastapi import FastAPI
        from api.ops_routes.colab_worker import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.post(
            "/colab-worker/register",
            json={"endpoint": _TUNNEL_URL},
            headers={"Authorization": f"Bearer {_API_KEY}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["endpoint"] == _TUNNEL_URL


def test_register_endpoint_wrong_key():
    with patch.dict(os.environ, {"COLAB_WORKER_API_KEY": _API_KEY}):
        from fastapi import FastAPI
        from api.ops_routes.colab_worker import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.post(
            "/colab-worker/register",
            json={"endpoint": _TUNNEL_URL},
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert resp.status_code == 401


def test_register_endpoint_no_auth():
    with patch.dict(os.environ, {"COLAB_WORKER_API_KEY": _API_KEY}):
        from fastapi import FastAPI
        from api.ops_routes.colab_worker import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.post("/colab-worker/register", json={"endpoint": _TUNNEL_URL})
        assert resp.status_code == 401


def test_register_endpoint_probe_timeout():
    import httpx

    with (
        patch(
            "api.ops_routes.colab_worker._probe_health",
            new=AsyncMock(side_effect=Exception("504")),
        ),
        patch.dict(os.environ, {"COLAB_WORKER_API_KEY": _API_KEY}),
    ):
        from fastapi import FastAPI
        from api.ops_routes.colab_worker import router
        from fastapi import HTTPException

        app = FastAPI()
        app.include_router(router)

        async def _timeout(_url, _key):
            raise HTTPException(status_code=504, detail="timeout")

        with patch("api.ops_routes.colab_worker._probe_health", new=AsyncMock(side_effect=HTTPException(status_code=504, detail="timeout"))):
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/colab-worker/register",
                json={"endpoint": _TUNNEL_URL},
                headers={"Authorization": f"Bearer {_API_KEY}"},
            )
            assert resp.status_code == 504


def test_register_endpoint_probe_unhealthy():
    from fastapi import HTTPException

    with (
        patch(
            "api.ops_routes.colab_worker._probe_health",
            new=AsyncMock(side_effect=HTTPException(status_code=502, detail="unhealthy")),
        ),
        patch.dict(os.environ, {"COLAB_WORKER_API_KEY": _API_KEY}),
    ):
        from fastapi import FastAPI
        from api.ops_routes.colab_worker import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(
            "/colab-worker/register",
            json={"endpoint": _TUNNEL_URL},
            headers={"Authorization": f"Bearer {_API_KEY}"},
        )
        assert resp.status_code == 502


def test_env_not_written_in_production():
    with (
        patch("api.ops_routes.colab_worker._probe_health", new=AsyncMock(return_value={"healthy": True})),
        patch("api.providers.dispatcher.dispatcher.update_provider_endpoint"),
        patch("api.services.provider_health.health_monitor.probe_provider", new=AsyncMock()),
        patch.dict(os.environ, {"COLAB_WORKER_API_KEY": _API_KEY, "ENVIRONMENT": "production"}),
    ):
        from fastapi import FastAPI
        from api.ops_routes.colab_worker import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.post(
            "/colab-worker/register",
            json={"endpoint": _TUNNEL_URL},
            headers={"Authorization": f"Bearer {_API_KEY}"},
        )
        assert resp.status_code == 200
        assert resp.json()["env_written"] is False


# ---------------------------------------------------------------------------
# _write_env_file
# ---------------------------------------------------------------------------


def test_write_env_file_updates_existing_key(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("FOO=bar\nCOLAB_WORKER_ENDPOINT=old\nBAZ=qux\n")

    from api.ops_routes.colab_worker import _write_env_file

    with patch("api.ops_routes.colab_worker._ENV_FILE_PATH", env_file):
        result = _write_env_file("COLAB_WORKER_ENDPOINT", "https://new.trycloudflare.com")

    assert result is True
    content = env_file.read_text()
    assert "COLAB_WORKER_ENDPOINT=https://new.trycloudflare.com" in content
    assert "old" not in content
    assert "FOO=bar" in content
    assert "BAZ=qux" in content


def test_write_env_file_appends_missing_key(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("FOO=bar\n")

    from api.ops_routes.colab_worker import _write_env_file

    with patch("api.ops_routes.colab_worker._ENV_FILE_PATH", env_file):
        result = _write_env_file("COLAB_WORKER_ENDPOINT", _TUNNEL_URL)

    assert result is True
    assert f"COLAB_WORKER_ENDPOINT={_TUNNEL_URL}" in env_file.read_text()


def test_write_env_file_missing_file(tmp_path: Path):
    from api.ops_routes.colab_worker import _write_env_file

    with patch("api.ops_routes.colab_worker._ENV_FILE_PATH", tmp_path / "nonexistent.env"):
        result = _write_env_file("COLAB_WORKER_ENDPOINT", _TUNNEL_URL)

    assert result is False
