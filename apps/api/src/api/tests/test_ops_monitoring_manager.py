"""Tests for MonitoringManager and the monitoring facade helpers.

The manager fans metrics and alerts out to whichever integrations were
configured and must not let one failing backend take down the others. The
facade wraps it with the alert payloads the ops surface actually sends.
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.ops.integrations import monitoring_facade as facade
from api.ops.integrations.manager import MonitoringManager


def _integration(
    *, enabled: bool = True, metrics: Any = True, alert: Any = True, config: Dict[str, Any] = None
) -> MagicMock:
    integration = MagicMock()
    integration.enabled = enabled
    integration.config = config if config is not None else {}
    integration.send_metrics = AsyncMock(
        side_effect=metrics if isinstance(metrics, Exception) else None,
        return_value=None if isinstance(metrics, Exception) else metrics,
    )
    integration.send_alert = AsyncMock(
        side_effect=alert if isinstance(alert, Exception) else None,
        return_value=None if isinstance(alert, Exception) else alert,
    )
    return integration


class TestManagerInitialize:
    @pytest.mark.asyncio
    async def test_registers_only_the_configured_backends(self):
        manager = MonitoringManager()

        await manager.initialize({"prometheus": {"enabled": False}})

        assert set(manager.integrations) == {"prometheus"}

    @pytest.mark.asyncio
    async def test_registers_every_supported_backend(self):
        manager = MonitoringManager()

        # Every one of these must be constructible; Prometheus and AlertManager
        # were previously abstract, so this call raised TypeError outright.
        await manager.initialize(
            {
                "datadog": {"enabled": False},
                "prometheus": {"enabled": False},
                "alertmanager": {"enabled": False},
            }
        )

        assert set(manager.integrations) == {"datadog", "prometheus", "alertmanager"}

    @pytest.mark.asyncio
    async def test_empty_config_registers_nothing(self):
        manager = MonitoringManager()

        await manager.initialize({})

        assert manager.integrations == {}

    @pytest.mark.asyncio
    async def test_keeps_the_supplied_config(self):
        manager = MonitoringManager()
        config = {"datadog": {"enabled": False}}

        await manager.initialize(config)

        assert manager.config == config


class TestManagerSendMetrics:
    @pytest.mark.asyncio
    async def test_reports_per_integration_results(self):
        manager = MonitoringManager()
        manager.integrations = {
            "ok": _integration(metrics=True),
            "refused": _integration(metrics=False),
        }

        results = await manager.send_metrics({"a": 1})

        assert results == {"ok": True, "refused": False}

    @pytest.mark.asyncio
    async def test_one_raising_backend_does_not_stop_the_others(self):
        manager = MonitoringManager()
        manager.integrations = {
            "boom": _integration(metrics=RuntimeError("offline")),
            "ok": _integration(metrics=True),
        }

        results = await manager.send_metrics({"a": 1})

        assert results == {"boom": False, "ok": True}

    @pytest.mark.asyncio
    async def test_no_integrations_yields_no_results(self):
        assert await MonitoringManager().send_metrics({"a": 1}) == {}


class TestManagerSendAlert:
    @pytest.mark.asyncio
    async def test_reports_per_integration_results(self):
        manager = MonitoringManager()
        manager.integrations = {
            "ok": _integration(alert=True),
            "refused": _integration(alert=False),
        }

        results = await manager.send_alert({"title": "x"})

        assert results == {"ok": True, "refused": False}

    @pytest.mark.asyncio
    async def test_one_raising_backend_does_not_stop_the_others(self):
        manager = MonitoringManager()
        manager.integrations = {
            "boom": _integration(alert=RuntimeError("offline")),
            "ok": _integration(alert=True),
        }

        results = await manager.send_alert({"title": "x"})

        assert results == {"boom": False, "ok": True}

    @pytest.mark.asyncio
    async def test_no_integrations_yields_no_results(self):
        assert await MonitoringManager().send_alert({"title": "x"}) == {}


class TestManagerStatus:
    @pytest.mark.asyncio
    async def test_masks_credentials(self):
        manager = MonitoringManager()
        manager.integrations = {
            "datadog": _integration(
                config={"api_key": "secret", "app_key": "secret2", "site": "datadoghq.com"}
            )
        }

        status = await manager.get_status()

        assert status["datadog"]["config"]["api_key"] == "****"
        assert status["datadog"]["config"]["app_key"] == "****"
        assert status["datadog"]["config"]["site"] == "datadoghq.com"

    @pytest.mark.asyncio
    async def test_reports_the_enabled_flag(self):
        manager = MonitoringManager()
        manager.integrations = {"p": _integration(enabled=False, config={})}

        status = await manager.get_status()

        assert status["p"]["enabled"] is False

    @pytest.mark.asyncio
    async def test_status_of_nothing_is_empty(self):
        assert await MonitoringManager().get_status() == {}


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------


class TestFacade:
    @pytest.mark.asyncio
    async def test_initialize_delegates_to_the_manager(self):
        with patch.object(facade.monitoring_manager, "initialize", AsyncMock()) as initialize:
            await facade.initialize_monitoring({"datadog": {}})

        initialize.assert_awaited_once_with({"datadog": {}})

    @pytest.mark.asyncio
    async def test_send_system_metrics_aggregates_then_fans_out(self):
        with (
            patch.object(facade.aggregator, "initialize", AsyncMock()),
            patch.object(
                facade.aggregator, "aggregate_system_metrics", AsyncMock(return_value={"m": 1})
            ),
            patch.object(
                facade.monitoring_manager, "send_metrics", AsyncMock(return_value={"dd": True})
            ) as send,
        ):
            results = await facade.send_system_metrics()

        assert results == {"dd": True}
        send.assert_awaited_once_with({"m": 1})

    @pytest.mark.asyncio
    async def test_send_system_metrics_swallows_aggregation_failures(self):
        with patch.object(
            facade.aggregator, "initialize", AsyncMock(side_effect=RuntimeError("no data"))
        ):
            assert await facade.send_system_metrics() == {}

    @pytest.mark.asyncio
    async def test_send_system_alert_returns_manager_results(self):
        with patch.object(
            facade.monitoring_manager, "send_alert", AsyncMock(return_value={"am": True})
        ):
            assert await facade.send_system_alert({"title": "x"}) == {"am": True}

    @pytest.mark.asyncio
    async def test_send_system_alert_swallows_failures(self):
        with patch.object(
            facade.monitoring_manager, "send_alert", AsyncMock(side_effect=RuntimeError("down"))
        ):
            assert await facade.send_system_alert({"title": "x"}) == {}

    @pytest.mark.asyncio
    async def test_get_monitoring_status_delegates(self):
        with patch.object(
            facade.monitoring_manager, "get_status", AsyncMock(return_value={"dd": {}})
        ):
            assert await facade.get_monitoring_status() == {"dd": {}}


class TestFacadeAlertHelpers:
    @pytest.mark.asyncio
    async def test_health_alert_is_silent_above_the_threshold(self):
        with patch.object(facade, "send_system_alert", AsyncMock()) as send:
            assert await facade.send_health_alert(90.0) == {}

        send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_health_alert_warns_between_50_and_the_threshold(self):
        with patch.object(facade, "send_system_alert", AsyncMock(return_value={})) as send:
            await facade.send_health_alert(60.0)

        assert send.await_args.args[0]["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_health_alert_is_critical_below_50(self):
        with patch.object(facade, "send_system_alert", AsyncMock(return_value={})) as send:
            await facade.send_health_alert(20.0)

        alert = send.await_args.args[0]
        assert alert["severity"] == "critical"
        assert "20.0" in alert["message"]

    @pytest.mark.asyncio
    async def test_health_alert_respects_a_custom_threshold(self):
        with patch.object(facade, "send_system_alert", AsyncMock(return_value={})) as send:
            await facade.send_health_alert(80.0, threshold=95.0)

        send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_provider_alert_is_silent_when_healthy(self):
        with patch.object(facade, "send_system_alert", AsyncMock()) as send:
            assert await facade.send_provider_alert("openai", "healthy", 10.0) == {}

        send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_provider_alert_is_critical_for_a_critical_provider(self):
        with patch.object(facade, "send_system_alert", AsyncMock(return_value={})) as send:
            await facade.send_provider_alert("groq", "critical", 900.0)

        alert = send.await_args.args[0]
        assert alert["severity"] == "critical"
        assert alert["instance"] == "groq"
        assert "groq" in alert["runbook_url"]

    @pytest.mark.asyncio
    async def test_provider_alert_warns_for_a_degraded_provider(self):
        with patch.object(facade, "send_system_alert", AsyncMock(return_value={})) as send:
            await facade.send_provider_alert("groq", "degraded", 400.0)

        assert send.await_args.args[0]["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_circuit_breaker_alert_only_fires_when_open(self):
        with patch.object(facade, "send_system_alert", AsyncMock()) as send:
            assert await facade.send_circuit_breaker_alert("openai", "CLOSED") == {}

        send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_circuit_breaker_alert_names_the_provider(self):
        with patch.object(facade, "send_system_alert", AsyncMock(return_value={})) as send:
            await facade.send_circuit_breaker_alert("openai", "OPEN")

        alert = send.await_args.args[0]
        assert "openai" in alert["title"]
        assert alert["severity"] == "warning"
        assert "openai" in alert["generator_url"]
