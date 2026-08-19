from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.services import provider_health
from api.services.provider_health import ProviderHealth, ProviderHealthService


@pytest.mark.asyncio
async def test_passive_observation_updates_available_state() -> None:
    service = ProviderHealthService(
        check_interval=1.0,
        probe_timeout_seconds=1.0,
        startup_jitter_seconds=0.0,
        periodic_jitter_seconds=0.0,
    )
    service.health_data["openai"] = ProviderHealth(provider_id="openai", configured=True)

    await service.observe_request("openai", ok=True, latency_ms=125.0)

    status = service.get_status("openai")
    assert status["status"] == "healthy"
    assert status["availability_state"] == "healthy"
    assert status["latency_ewma_ms"] == pytest.approx(125.0)
    assert service.is_available("openai") is True


@pytest.mark.asyncio
async def test_probe_provider_transitions_unknown_to_healthy(monkeypatch) -> None:
    dispatcher = SimpleNamespace(
        check_provider=AsyncMock(
            return_value={
                "configured": True,
                "healthy": True,
                "billing_issue": False,
                "latency_ms": 42.0,
                "health_reason": "",
            }
        ),
        is_configured=lambda provider_id: True,
        get_provider_config=lambda provider_id: {"default_model": "gpt-4o-mini"},
        get_provider=lambda provider_id: SimpleNamespace(
            warmup=AsyncMock(return_value=SimpleNamespace(ok=True, latency_ms=11.0))
        ),
    )
    monkeypatch.setattr(provider_health, "_dispatcher", lambda: dispatcher)

    service = ProviderHealthService(
        check_interval=1.0,
        probe_timeout_seconds=1.0,
        startup_jitter_seconds=0.0,
        periodic_jitter_seconds=0.0,
    )

    await service.probe_provider("openai")

    status = service.get_status("openai")
    assert status["status"] == "healthy"
    assert status["configured"] is True
    assert status["latency_ewma_ms"] == pytest.approx(42.0)
    assert service.is_available("openai") is True
    assert dispatcher.check_provider.await_count == 1


@pytest.mark.asyncio
async def test_start_schedules_background_probe_without_blocking(monkeypatch) -> None:
    dispatcher = SimpleNamespace(
        list_providers=lambda include_hidden=False: [{"id": "openai", "configured": True}],
        is_configured=lambda provider_id: True,
        check_provider=AsyncMock(
            return_value={
                "configured": True,
                "healthy": True,
                "billing_issue": False,
                "latency_ms": 10.0,
                "health_reason": "",
            }
        ),
        get_provider_config=lambda provider_id: {"default_model": "gpt-4o-mini"},
        get_provider=lambda provider_id: SimpleNamespace(
            warmup=AsyncMock(return_value=SimpleNamespace(ok=True, latency_ms=10.0))
        ),
    )
    monkeypatch.setattr(provider_health, "_dispatcher", lambda: dispatcher)

    created: list[object] = []

    def fake_create_task(coro):
        coro.close()
        task = SimpleNamespace(cancel=lambda: None)
        created.append(task)
        return task

    monkeypatch.setattr(provider_health.asyncio, "create_task", fake_create_task)

    service = ProviderHealthService(
        check_interval=1.0,
        probe_timeout_seconds=1.0,
        startup_jitter_seconds=0.0,
        periodic_jitter_seconds=0.0,
    )

    await service.start()

    assert service._running is True
    assert created
    assert dispatcher.check_provider.await_count == 0
