"""Coverage for api.health aggregation and subsystem probes."""

from __future__ import annotations

from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api import health
from api.security_config import SecurityConfig
from api.services import provider_health


class _DummyConn:
    def __init__(self) -> None:
        self.execute = AsyncMock(return_value=None)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _DummyEngine:
    def __init__(self) -> None:
        self._conn = _DummyConn()

    def connect(self):
        return self._conn


def _provider_health_monitor(
    status_payload: dict[str, dict[str, str]],
) -> MagicMock:
    monitor = MagicMock()
    monitor.get_all_status = MagicMock(return_value=status_payload)
    return monitor


@pytest.mark.asyncio
async def test_health_returns_healthy_when_everything_passes() -> None:
    provider_monitor = _provider_health_monitor(
        {
            "openai": {"status": "healthy"},
            "anthropic": {"status": "billing_issue"},
        }
    )

    with (
        patch.object(
            health,
            "check_routing_health",
            new=AsyncMock(return_value={"status": "healthy"}),
        ),
        patch.object(
            health,
            "check_db_health",
            new=AsyncMock(return_value={"status": "healthy"}),
        ),
        patch.object(
            health,
            "check_redis_health",
            new=AsyncMock(return_value={"status": "healthy"}),
        ),
        patch.object(
            health,
            "check_api_health",
            new=AsyncMock(return_value={"status": "healthy"}),
        ),
        patch.object(
            provider_health,
            "health_monitor",
            provider_monitor,
            create=True,
        ),
        patch.object(
            SecurityConfig,
            "validate_config",
            return_value=[],
        ),
        patch.object(SecurityConfig, "DEBUG", False),
        patch.object(
            SecurityConfig,
            "ALLOWED_ORIGINS",
            ["https://example.com"],
            create=True,
        ),
    ):
        response = await health.health_check()

    assert response.data["status"] == "healthy"
    assert response.data["components"]["providers"]["status"] == "healthy"
    provider_monitor.get_all_status.assert_called_once_with(include_hidden=False)


@pytest.mark.asyncio
async def test_health_returns_degraded_when_db_fails() -> None:
    provider_monitor = _provider_health_monitor({"openai": {"status": "healthy"}})

    with ExitStack() as stack:
        stack.enter_context(
            patch.object(
                provider_health,
                "health_monitor",
                provider_monitor,
                create=True,
            )
        )
        stack.enter_context(
            patch.object(
                health,
                "check_routing_health",
                new=AsyncMock(return_value={"status": "healthy"}),
            )
        )
        stack.enter_context(
            patch.object(
                health,
                "check_db_health",
                new=AsyncMock(return_value={"status": "degraded"}),
            )
        )
        stack.enter_context(
            patch.object(
                health,
                "check_redis_health",
                new=AsyncMock(return_value={"status": "healthy"}),
            )
        )
        stack.enter_context(
            patch.object(
                health,
                "check_api_health",
                new=AsyncMock(return_value={"status": "healthy"}),
            )
        )
        stack.enter_context(
            patch.object(
                SecurityConfig,
                "validate_config",
                return_value=[],
            )
        )
        stack.enter_context(patch.object(SecurityConfig, "DEBUG", False))
        stack.enter_context(
            patch.object(
                SecurityConfig,
                "ALLOWED_ORIGINS",
                ["https://example.com"],
                create=True,
            )
        )
        response = await health.health_check()

    assert response.data["status"] == "degraded"
    assert response.data["components"]["database"]["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_returns_warnings_on_security_issues() -> None:
    provider_monitor = _provider_health_monitor({"openai": {"status": "healthy"}})

    with ExitStack() as stack:
        stack.enter_context(
            patch.object(
                provider_health,
                "health_monitor",
                provider_monitor,
                create=True,
            )
        )
        stack.enter_context(
            patch.object(
                health,
                "check_routing_health",
                new=AsyncMock(return_value={"status": "healthy"}),
            )
        )
        stack.enter_context(
            patch.object(
                health,
                "check_db_health",
                new=AsyncMock(return_value={"status": "healthy"}),
            )
        )
        stack.enter_context(
            patch.object(
                health,
                "check_redis_health",
                new=AsyncMock(return_value={"status": "healthy"}),
            )
        )
        stack.enter_context(
            patch.object(
                health,
                "check_api_health",
                new=AsyncMock(return_value={"status": "healthy"}),
            )
        )
        stack.enter_context(
            patch.object(
                SecurityConfig,
                "validate_config",
                return_value=["missing allowed origin"],
            )
        )
        stack.enter_context(patch.object(SecurityConfig, "DEBUG", True))
        stack.enter_context(
            patch.object(
                SecurityConfig,
                "ALLOWED_ORIGINS",
                [],
                create=True,
            )
        )
        response = await health.health_check()

    assert response.data["status"] == "warnings"
    assert response.data["components"]["security"]["status"] == "warnings"


@pytest.mark.asyncio
async def test_check_db_health_success_and_failure() -> None:
    with patch("api.storage.database.engine", new=_DummyEngine()):
        healthy = await health.check_db_health()

    assert healthy["status"] == "healthy"

    class _BrokenEngine:
        def connect(self):
            raise RuntimeError("database down")

    with patch("api.storage.database.engine", new=_BrokenEngine()):
        unhealthy = await health.check_db_health()

    assert unhealthy["status"] == "unhealthy"
    assert "Database connection failed" in unhealthy["error"]


@pytest.mark.asyncio
async def test_check_redis_health_success_and_failure() -> None:
    fake_redis = AsyncMock()
    fake_redis.ping = AsyncMock(return_value=True)
    fake_redis.set = AsyncMock(return_value=True)
    fake_redis.get = AsyncMock(return_value="test_value")
    fake_redis.delete = AsyncMock(return_value=True)
    fake_redis.info = AsyncMock(
        return_value={
            "used_memory_human": "1MB",
            "connected_clients": 4,
            "uptime_in_days": 7,
        }
    )

    with patch("api.storage.cache.cache._redis", fake_redis):
        healthy = await health.check_redis_health()

    assert healthy["status"] == "healthy"
    assert healthy["connection"] == "available"
    assert healthy["memory_used"] == "1MB"

    fake_redis.ping.side_effect = ConnectionError("redis down")
    with patch("api.storage.cache.cache._redis", fake_redis):
        unhealthy = await health.check_redis_health()

    assert unhealthy["status"] == "unhealthy"
    assert "Redis connection failed" in unhealthy["error"]


@pytest.mark.asyncio
async def test_check_routing_health_success_and_failure() -> None:
    with patch(
        "api.routing_router.top_providers_for",
        return_value=["openai", "anthropic"],
    ):
        healthy = await health.check_routing_health()

    assert healthy["status"] == "healthy"
    assert healthy["providers_available"] == 2

    with patch(
        "api.routing_router.top_providers_for",
        side_effect=RuntimeError("router exploded"),
    ):
        degraded = await health.check_routing_health()

    assert degraded["status"] == "degraded"
    assert "router exploded" in degraded["error"]


# End of health coverage tests.
HEALTH_TESTS_READY = True
