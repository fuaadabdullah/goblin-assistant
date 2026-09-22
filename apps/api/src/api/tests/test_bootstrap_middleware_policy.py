"""Bootstrap/startup middleware policy tests (fail-fast production guards)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.bootstrap.middleware import (
    install_runtime_middlewares,
    resolve_runtime_origins,
)
from api.middleware.rate_limiter import RateLimiter


def _app_without_routes() -> FastAPI:
    return FastAPI()


def test_resolve_runtime_origins_rejects_wildcard_in_production():
    with pytest.raises(RuntimeError, match="wildcard"):
        resolve_runtime_origins(environment="production", configured=["*"])


def test_resolve_runtime_origins_rejects_empty_origins_in_production():
    with pytest.raises(RuntimeError, match="no CORS origins"):
        resolve_runtime_origins(environment="production", configured=[])


def test_resolve_runtime_origins_allows_explicit_origins_in_production(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com")
    resolved = resolve_runtime_origins(
        environment="production", configured=["https://app.example.com"]
    )
    assert resolved == ["https://app.example.com"]


def test_resolve_runtime_origins_permits_wildcard_outside_production():
    resolved = resolve_runtime_origins(environment="development", configured=["*"])
    assert resolved == ["*"]


def test_install_runtime_middlewares_fails_closed_without_origins_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", "")
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    monkeypatch.delenv("BACKEND_URL", raising=False)
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("LOCAL_LLM_API_KEY", "test-key")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    import importlib

    import api.security_config as security_config_module

    importlib.reload(security_config_module)
    try:
        with pytest.raises(RuntimeError, match="no explicit ALLOWED_ORIGINS"):
            install_runtime_middlewares(_app_without_routes(), environment="production")
    finally:
        importlib.reload(security_config_module)


def test_install_runtime_middlewares_requires_rate_limiting_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("LOCAL_LLM_API_KEY", "test-key")

    import importlib

    import api.security_config as security_config_module

    importlib.reload(security_config_module)
    try:
        with pytest.raises(RuntimeError, match="RATE_LIMIT_ENABLED"):
            install_runtime_middlewares(_app_without_routes(), environment="production")
    finally:
        importlib.reload(security_config_module)


def test_install_runtime_middlewares_keeps_chat_machine_key_protected(
    monkeypatch,
):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("LOCAL_LLM_API_KEY", "machine-key")

    app = FastAPI()

    @app.post("/api/v1/api/chat")
    async def chat():
        return {"message": "ok"}

    install_runtime_middlewares(app, environment="development")
    client = TestClient(app)

    unauthenticated = client.post("/api/v1/api/chat", json={})
    assert unauthenticated.status_code == 401

    authenticated = client.post("/api/v1/api/chat", json={}, headers={"x-api-key": "machine-key"})
    assert authenticated.status_code == 200


def test_rate_limiter_marks_backend_degraded_on_redis_failure(monkeypatch):
    limiter = RateLimiter(requests_per_minute=1, requests_per_hour=10, environment="test")

    async def _boom():
        raise ConnectionError("redis down")

    import api.middleware.rate_limiter as rate_limiter_module

    monkeypatch.setattr(rate_limiter_module, "get_redis_client", _boom)

    from fastapi import Request

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/api/chat",
        "headers": [],
        "client": ("127.0.0.1", 12345),
    }
    request = Request(scope)

    import anyio

    async def _run():
        first = await limiter.check_rate_limit(request)
        assert first["allowed"] is True
        assert limiter.backend_degraded is True
        second = await limiter.check_rate_limit(request)
        assert second["allowed"] is False

    anyio.run(_run)
