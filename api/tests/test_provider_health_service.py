"""Tests for api.services.provider_health."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.services.provider_health import (
    HealthStatus,
    ProviderHealth,
    ProviderHealthMonitor,
)


def test_provider_health_record_success_updates_state():
    state = ProviderHealth(provider_id="openai")

    state.record_success(123.4)

    assert state.status == HealthStatus.HEALTHY
    assert state.last_success is not None
    assert state.last_error is None
    assert state.consecutive_failures == 0
    assert state.avg_latency_ms == 123.4


def test_provider_health_record_failure_transitions_status():
    state = ProviderHealth(provider_id="openai")

    state.record_failure("timeout")
    assert state.status == HealthStatus.DEGRADED
    state.record_failure("timeout")
    state.record_failure("timeout")

    assert state.status == HealthStatus.UNHEALTHY
    assert state.consecutive_failures == 3


@pytest.mark.asyncio
async def test_refresh_updates_health_data():
    monitor = ProviderHealthMonitor()
    inventory = [
        {
            "id": "openai",
            "configured": True,
            "healthy": True,
            "latency_ms": 42,
        },
        {
            "id": "mock",
            "configured": False,
            "healthy": False,
            "health_reason": "not configured",
        },
    ]

    fake_stats = MagicMock()
    fake_stats.success_rate = 0.97

    with patch(
        "api.services.provider_health.dispatcher.get_provider_inventory",
        new_callable=AsyncMock,
        return_value=inventory,
    ), patch(
        "api.services.provider_health.registry.get",
        return_value=fake_stats,
    ):
        result = await monitor.refresh(include_hidden=False)

    assert "openai" in result
    assert result["openai"].status == HealthStatus.HEALTHY
    assert result["mock"].status == HealthStatus.UNKNOWN


@pytest.mark.asyncio
async def test_validate_configured_credentials_groups_ids():
    monitor = ProviderHealthMonitor()
    inventory = [
        {"id": "openai", "configured": True, "is_selectable": True},
        {"id": "mock", "configured": False, "is_selectable": False},
    ]

    with patch(
        "api.services.provider_health.dispatcher.get_provider_inventory",
        new_callable=AsyncMock,
        return_value=inventory,
    ):
        result = await monitor.validate_configured_credentials()

    assert result["configured"] == ["openai"]
    assert result["selectable"] == ["openai"]
    assert result["unconfigured"] == ["mock"]


@pytest.mark.asyncio
async def test_probe_provider_updates_state():
    monitor = ProviderHealthMonitor()
    fake_stats = MagicMock()
    fake_stats.success_rate = 0.91

    with patch(
        "api.services.provider_health.dispatcher.check_provider",
        new_callable=AsyncMock,
        return_value={
            "configured": True,
            "healthy": True,
            "latency_ms": 18,
            "health_reason": None,
        },
    ), patch(
        "api.services.provider_health.registry.get",
        return_value=fake_stats,
    ), patch(
        "api.services.provider_health.canonical_provider_id",
        return_value="openai",
    ):
        status = await monitor.probe_provider("openai")

    assert status["status"] == HealthStatus.HEALTHY.value
    assert status["configured"] is True


def test_is_available_uses_cached_state():
    monitor = ProviderHealthMonitor()
    state = ProviderHealth(provider_id="openai", configured=True)
    state.status = HealthStatus.DEGRADED
    monitor.health_data["openai"] = state

    assert monitor.is_available("openai") is True


def test_get_status_unknown_provider_returns_error():
    monitor = ProviderHealthMonitor()

    with patch(
        "api.services.provider_health.dispatcher.get_provider_config",
        return_value=None,
    ):
        result = monitor.get_status("missing")

    assert result["error"] == "Unknown provider: missing"


def test_get_best_providers_sorts_by_latency_and_success_rate():
    monitor = ProviderHealthMonitor()

    fast = ProviderHealth(provider_id="fast", configured=True)
    fast.status = HealthStatus.HEALTHY
    fast.avg_latency_ms = 10
    fast.success_rate = 0.99

    slow = ProviderHealth(provider_id="slow", configured=True)
    slow.status = HealthStatus.HEALTHY
    slow.avg_latency_ms = 50
    slow.success_rate = 0.95

    monitor.health_data = {"fast": fast, "slow": slow}

    assert monitor.get_best_providers(limit=1) == ["fast"]
