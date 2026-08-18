"""Focused runtime coverage for api.artifact_service."""

from __future__ import annotations

import importlib

from api import artifact_service as artifact_service_module


def test_artifact_service_ignores_invalid_redis_url(monkeypatch) -> None:
    monkeypatch.setenv("REDIS_URL", "not-a-redis-url")

    module = importlib.reload(artifact_service_module)

    assert module._resolve_redis_url("not-a-redis-url") == "redis://localhost:6379/0"
    assert module.artifact_service.redis_client is not None
