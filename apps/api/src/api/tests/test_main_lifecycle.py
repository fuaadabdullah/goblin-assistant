"""Runtime coverage for api.main startup/shutdown and app assembly."""

from __future__ import annotations

import asyncio
import os
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api import main
from api.services import provider_health


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
    assert "/health" in paths
    assert "/search/query" in paths


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
        stack.enter_context(
            patch.object(provider_health, "health_monitor", health_monitor)
        )
        stack.enter_context(
            patch.object(main.cache, "init_redis", fake_redis_init)
        )
        stack.enter_context(patch.object(main, "init_db", fake_db_init))
        stack.enter_context(
            patch.object(main.monitor, "start", fake_monitor_start)
        )
        stack.enter_context(
            patch.object(main.monitor, "stop", fake_monitor_stop)
        )
        stack.enter_context(
            patch.object(main.cache, "close", fake_cache_close)
        )
        stack.enter_context(
            patch.object(main, "init_secrets_adapter", fake_init_secrets)
        )
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

    with patch.dict(
        os.environ,
        {"FAIL_ON_PROVIDER_CREDENTIAL_ERRORS": "true"},
        clear=False,
    ):
        with ExitStack() as stack:
            stack.enter_context(
                patch.object(provider_health, "health_monitor", health_monitor)
            )
            stack.enter_context(
                patch.object(main.cache, "init_redis", fake_redis_init)
            )
            stack.enter_context(
                patch.object(main, "init_db", fake_db_init)
            )
            stack.enter_context(
                patch.object(main.monitor, "start", fake_monitor_start)
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
