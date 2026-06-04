"""Tests for Colab heartbeat service."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from api.services.colab_heartbeat import ColabHeartbeatService


@pytest.mark.asyncio
async def test_heartbeat_service_starts_and_stops_cleanly():
    service = ColabHeartbeatService()

    with (
        patch.object(service, "_enabled", return_value=True),
        patch.object(service, "_probe_if_configured", new=AsyncMock(return_value=True)),
        patch.object(service, "_heartbeat_loop", new=AsyncMock()),
    ):
        await service.start()
        assert service._running is True
        assert service._task is not None

        await service.stop()
        assert service._running is False
        assert service._task is None


@pytest.mark.asyncio
async def test_heartbeat_loop_probes_on_interval():
    service = ColabHeartbeatService()

    async def fast_sleep(_seconds: int) -> None:
        return None

    async def probe_once_then_stop() -> bool:
        service._running = False
        return True

    with patch("api.services.colab_heartbeat.asyncio.sleep", new=fast_sleep), patch.object(
        service,
        "_probe_if_configured",
        new=AsyncMock(side_effect=probe_once_then_stop),
    ) as probe_mock:
        service._running = True
        await service._heartbeat_loop()

    probe_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_probe_skips_when_colab_not_configured():
    service = ColabHeartbeatService()

    with (
        patch(
            "api.services.colab_heartbeat.dispatcher.get_provider_config",
            return_value={"name": "Colab Worker"},
        ),
        patch(
            "api.services.colab_heartbeat.dispatcher.is_configured",
            return_value=False,
        ),
        patch(
            "api.services.colab_heartbeat.health_monitor.probe_provider",
            new=AsyncMock(),
        ) as probe_provider,
    ):
        probed = await service._probe_if_configured()

    assert probed is False
    probe_provider.assert_not_awaited()
