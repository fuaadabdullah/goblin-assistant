"""Runtime coverage for api.main startup/shutdown and app assembly."""

from __future__ import annotations

import asyncio
import os
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api import lifespan as lifespan_module
from api import main


def _provider_health_stub(
    *,
    invalid_credentials: list[str] | None = None,
    unreachable: list[str] | None = None,
) -> MagicMock:
    health_monitor = MagicMock()
    health_monitor.start = AsyncMock(return_value=None)
    health_monitor.stop = AsyncMock(return_value=None)
    health_monitor.validate_configured_credentials = AsyncMock(
        return_value={
            "invalid_credentials": invalid_credentials or [],
            "unreachable": unreachable or [],
        }
    )
    health_monitor.get_all_status = MagicMock(return_value={})
    return health_monitor


def test_app_registers_runtime_middlewares_and_core_routes() -> None:
    assert len(main.app.user_middleware) >= 4

    paths = {route.path for route in main.app.routes if hasattr(route, "path")}
    assert "/" in paths
    assert "/test" in paths
    assert "/api/v1/health" in paths
    assert "/api/v1/search/query" in paths


def test_create_app_disables_docs_and_openapi_in_production(monkeypatch) -> None:
    from api.app_factory import create_app

    # Production guards require explicit CORS origins + enabled rate limiting;
    # supply both so this test exercises docs/openapi gating, not the guards
    # (which have their own dedicated coverage in test_bootstrap_middleware_policy).
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")

    app = create_app()

    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/docs" not in paths
    assert "/redoc" not in paths
    assert "/openapi.json" not in paths


def test_app_auth_middleware_excludes_public_auth_bootstrap_routes() -> None:
    auth_middleware = next(
        middleware
        for middleware in main.app.user_middleware
        if middleware.cls.__name__ == "AuthenticationMiddleware"
    )
    excluded_paths = set(auth_middleware.kwargs["exclude_paths"])

    assert "/health" in excluded_paths
    assert "/auth/csrf-token" in excluded_paths
    assert "/auth/google/url" in excluded_paths
    assert "/auth/passkey/challenge" in excluded_paths


@pytest.mark.asyncio
async def test_lifespan_startup_and_shutdown_calls_integrations() -> None:
    health_monitor = _provider_health_stub()

    fake_redis_init = AsyncMock(return_value=None)
    fake_db_init = AsyncMock(return_value=True)
    fake_monitor_start = AsyncMock(return_value=None)
    fake_monitor_stop = AsyncMock(return_value=None)
    fake_cache_close = AsyncMock(return_value=None)
    fake_init_secrets = AsyncMock(return_value=None)
    fake_cleanup_secrets = AsyncMock(return_value=None)
    fake_cleanup_start = AsyncMock(return_value=None)
    fake_cleanup_stop = AsyncMock(return_value=None)

    with ExitStack() as stack:
        stack.enter_context(patch.object(lifespan_module, "health_monitor", health_monitor))
        stack.enter_context(patch.object(main.cache, "init_redis", fake_redis_init))
        stack.enter_context(patch.object(main, "init_db", fake_db_init))
        stack.enter_context(patch.object(main.monitor, "start", fake_monitor_start))
        stack.enter_context(patch.object(main.monitor, "stop", fake_monitor_stop))
        stack.enter_context(patch.object(main.cache, "close", fake_cache_close))
        stack.enter_context(patch.object(main, "init_secrets_adapter", fake_init_secrets))
        stack.enter_context(
            patch.object(
                main,
                "cleanup_secrets_adapter",
                fake_cleanup_secrets,
            )
        )
        stack.enter_context(
            patch.object(
                main.artifact_cleanup_service,
                "start",
                fake_cleanup_start,
            )
        )
        stack.enter_context(
            patch.object(
                main.artifact_cleanup_service,
                "stop",
                fake_cleanup_stop,
            )
        )
        async with main.lifespan(main.app):
            await asyncio.sleep(0)

    fake_redis_init.assert_awaited_once()
    fake_db_init.assert_awaited_once()
    fake_monitor_start.assert_awaited_once()
    health_monitor.start.assert_awaited_once()
    health_monitor.validate_configured_credentials.assert_awaited_once()
    fake_init_secrets.assert_awaited_once()
    fake_cleanup_start.assert_awaited_once()
    fake_monitor_stop.assert_awaited_once()
    fake_cache_close.assert_awaited_once()
    fake_cleanup_secrets.assert_awaited_once()
    fake_cleanup_stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_logs_bad_provider_creds_but_continues() -> None:
    health_monitor = _provider_health_stub(
        invalid_credentials=["openai"],
    )

    fake_redis_init = AsyncMock(return_value=None)
    fake_db_init = AsyncMock(return_value=True)
    fake_monitor_start = AsyncMock(return_value=None)
    fake_cleanup_start = AsyncMock(return_value=None)
    fake_init_secrets = AsyncMock(return_value=None)

    with (
        patch.dict(
            os.environ,
            {"FAIL_ON_PROVIDER_CREDENTIAL_ERRORS": "true"},
            clear=False,
        ),
        ExitStack() as stack,
    ):
        stack.enter_context(patch.object(lifespan_module, "health_monitor", health_monitor))
        stack.enter_context(patch.object(main.cache, "init_redis", fake_redis_init))
        stack.enter_context(patch.object(main, "init_db", fake_db_init))
        stack.enter_context(patch.object(main.monitor, "start", fake_monitor_start))
        stack.enter_context(
            patch.object(
                main.artifact_cleanup_service,
                "start",
                fake_cleanup_start,
            )
        )
        stack.enter_context(
            patch.object(
                main,
                "init_secrets_adapter",
                fake_init_secrets,
            )
        )
        async with main.lifespan(main.app):
            await asyncio.sleep(0)

    fake_redis_init.assert_awaited_once()
    fake_db_init.assert_awaited_once()
    fake_monitor_start.assert_awaited_once()
    health_monitor.start.assert_awaited_once()
    health_monitor.validate_configured_credentials.assert_awaited_once()
    fake_init_secrets.assert_awaited_once()
    fake_cleanup_start.assert_awaited_once()
