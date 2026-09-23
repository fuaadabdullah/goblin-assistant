"""Tests for the DataDog / Prometheus / AlertManager monitoring integrations.

Each integration is an HTTP client behind a small capability contract, so the
tests drive fake httpx clients and assert on the payloads that would go out.
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.ops.integrations.providers import (
    AlertManagerIntegration,
    DataDogIntegration,
    PrometheusIntegration,
)

_METRICS: Dict[str, Any] = {
    "environment": "prod",
    "health": {"overall_score": 87},
    "providers": {
        "openai": {"health_score": 91, "latency_ms": 120, "status": "healthy"},
        "groq": {"health_score": 40, "latency_ms": 900, "status": "critical"},
    },
    "performance": {"aggregated": {"p95_ms": 210}},
    "streaming": {"comparison": {"ttfb_ms": 80}},
}


def _client(response) -> MagicMock:
    client = MagicMock()
    client.post = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


class _Resp:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


async def _enabled_datadog() -> DataDogIntegration:
    integration = DataDogIntegration()
    await integration.initialize({"enabled": True, "api_key": "k", "app_key": "a"})
    return integration


async def _enabled_prometheus() -> PrometheusIntegration:
    integration = PrometheusIntegration()
    await integration.initialize(
        {"enabled": True, "metrics_endpoint": "http://pushgw.example/metrics"}
    )
    return integration


async def _enabled_alertmanager() -> AlertManagerIntegration:
    integration = AlertManagerIntegration()
    await integration.initialize({"enabled": True, "alertmanager_url": "http://am.example"})
    return integration


# ---------------------------------------------------------------------------
# Capability contract
# ---------------------------------------------------------------------------


class TestCapabilityContract:
    """Every integration must be constructible.

    send_metrics and send_alert are both abstract on MonitoringIntegration.
    Prometheus previously omitted send_alert and AlertManager omitted
    send_metrics, which made them abstract and impossible to instantiate —
    MonitoringManager.initialize() raised TypeError for any config naming
    them, so neither backend could ever be used.
    """

    @pytest.mark.parametrize(
        "cls", [DataDogIntegration, PrometheusIntegration, AlertManagerIntegration]
    )
    def test_integration_can_be_constructed(self, cls):
        assert cls().enabled is False

    @pytest.mark.asyncio
    async def test_prometheus_declines_alerts(self):
        integration = await _enabled_prometheus()

        assert await integration.send_alert({"title": "x"}) is False

    @pytest.mark.asyncio
    async def test_alertmanager_declines_metrics(self):
        integration = await _enabled_alertmanager()

        assert await integration.send_metrics(_METRICS) is False


# ---------------------------------------------------------------------------
# initialize
# ---------------------------------------------------------------------------


class TestInitialize:
    @pytest.mark.asyncio
    async def test_datadog_requires_both_keys(self):
        integration = DataDogIntegration()

        assert await integration.initialize({"enabled": True, "api_key": "k"}) is False

    @pytest.mark.asyncio
    async def test_datadog_succeeds_with_both_keys(self):
        integration = DataDogIntegration()

        assert await integration.initialize({"enabled": True, "api_key": "k", "app_key": "a"})
        assert integration.api_key == "k"
        assert integration.app_key == "a"

    @pytest.mark.asyncio
    async def test_disabled_config_short_circuits(self):
        integration = DataDogIntegration()

        assert await integration.initialize({"enabled": False, "api_key": "k", "app_key": "a"}) is (
            False
        )

    @pytest.mark.asyncio
    async def test_prometheus_requires_an_endpoint(self):
        integration = PrometheusIntegration()

        assert await integration.initialize({"enabled": True}) is False

    @pytest.mark.asyncio
    async def test_prometheus_stores_the_endpoint(self):
        integration = await _enabled_prometheus()

        assert integration.metrics_endpoint == "http://pushgw.example/metrics"

    @pytest.mark.asyncio
    async def test_alertmanager_requires_a_url(self):
        integration = AlertManagerIntegration()

        assert await integration.initialize({"enabled": True}) is False

    @pytest.mark.asyncio
    async def test_alertmanager_stores_the_url(self):
        integration = await _enabled_alertmanager()

        assert integration.alertmanager_url == "http://am.example"


# ---------------------------------------------------------------------------
# DataDog
# ---------------------------------------------------------------------------


class TestDataDogMetrics:
    @pytest.mark.asyncio
    async def test_refuses_to_send_when_disabled(self):
        assert await DataDogIntegration().send_metrics(_METRICS) is False

    @pytest.mark.asyncio
    async def test_accepts_a_202_response(self):
        integration = await _enabled_datadog()
        client = _client(_Resp(202))

        with patch("httpx.AsyncClient", return_value=client):
            assert await integration.send_metrics(_METRICS) is True

        headers = client.post.await_args.kwargs["headers"]
        assert headers["DD-API-KEY"] == "k"
        assert headers["DD-APPLICATION-KEY"] == "a"

    @pytest.mark.asyncio
    async def test_treats_other_statuses_as_failure(self):
        integration = await _enabled_datadog()

        with patch("httpx.AsyncClient", return_value=_client(_Resp(400, "bad"))):
            assert await integration.send_metrics(_METRICS) is False

    @pytest.mark.asyncio
    async def test_network_errors_are_swallowed(self):
        integration = await _enabled_datadog()

        with patch("httpx.AsyncClient", side_effect=RuntimeError("offline")):
            assert await integration.send_metrics(_METRICS) is False

    def test_transform_emits_one_series_per_measurement(self):
        integration = DataDogIntegration()

        series = integration._transform_to_datadog_format(_METRICS)
        names = [s["metric"] for s in series]

        assert "goblin.assistant.system.health_score" in names
        # three per provider, two providers
        assert names.count("goblin.assistant.provider.health_score") == 2
        assert names.count("goblin.assistant.provider.latency_ms") == 2
        assert names.count("goblin.assistant.provider.status") == 2
        assert "goblin.assistant.performance.p95_ms" in names
        assert "goblin.assistant.streaming.ttfb_ms" in names

    def test_transform_maps_status_strings_to_numbers(self):
        integration = DataDogIntegration()

        series = integration._transform_to_datadog_format(_METRICS)
        status_points = {
            s["tags"][1]: s["points"][0][1]
            for s in series
            if s["metric"] == "goblin.assistant.provider.status"
        }

        assert status_points["provider:openai"] == 1
        assert status_points["provider:groq"] == 0

    def test_transform_scores_a_degraded_provider_between_the_extremes(self):
        integration = DataDogIntegration()

        series = integration._transform_to_datadog_format(
            {"providers": {"p": {"status": "degraded"}}}
        )
        status = next(s for s in series if s["metric"] == "goblin.assistant.provider.status")

        assert status["points"][0][1] == 0.5

    def test_transform_defaults_unknown_status_to_zero(self):
        integration = DataDogIntegration()

        series = integration._transform_to_datadog_format({"providers": {"p": {}}})
        status = next(s for s in series if s["metric"] == "goblin.assistant.provider.status")

        assert status["points"][0][1] == 0

    def test_transform_of_empty_metrics_is_empty(self):
        assert DataDogIntegration()._transform_to_datadog_format({}) == []

    def test_transform_tags_carry_the_environment(self):
        integration = DataDogIntegration()

        series = integration._transform_to_datadog_format(_METRICS)

        assert all("environment:prod" in s["tags"] for s in series)

    def test_transform_defaults_missing_environment_to_unknown(self):
        integration = DataDogIntegration()

        series = integration._transform_to_datadog_format({"health": {"overall_score": 1}})

        assert "environment:unknown" in series[0]["tags"]


class TestDataDogAlerts:
    @pytest.mark.asyncio
    async def test_refuses_to_send_when_disabled(self):
        assert await DataDogIntegration().send_alert({"title": "x"}) is False

    @pytest.mark.asyncio
    async def test_accepts_200_and_201(self):
        integration = await _enabled_datadog()

        for status in (200, 201):
            with patch("httpx.AsyncClient", return_value=_client(_Resp(status))):
                assert await integration.send_alert({"title": "Down"}) is True

    @pytest.mark.asyncio
    async def test_other_statuses_are_failures(self):
        integration = await _enabled_datadog()

        with patch("httpx.AsyncClient", return_value=_client(_Resp(403, "nope"))):
            assert await integration.send_alert({"title": "Down"}) is False

    @pytest.mark.asyncio
    async def test_errors_are_swallowed(self):
        integration = await _enabled_datadog()

        with patch("httpx.AsyncClient", side_effect=RuntimeError("offline")):
            assert await integration.send_alert({"title": "Down"}) is False

    @pytest.mark.asyncio
    async def test_monitor_payload_uses_supplied_fields(self):
        integration = await _enabled_datadog()
        client = _client(_Resp(200))

        with patch("httpx.AsyncClient", return_value=client):
            await integration.send_alert(
                {"title": "Custom", "query": "avg(last_1m):x > 1", "message": "m"}
            )

        body = client.post.await_args.kwargs["json"]
        assert body["name"] == "Custom"
        assert body["query"] == "avg(last_1m):x > 1"
        assert body["message"] == "m"

    @pytest.mark.asyncio
    async def test_monitor_payload_falls_back_to_defaults(self):
        integration = await _enabled_datadog()
        client = _client(_Resp(200))

        with patch("httpx.AsyncClient", return_value=client):
            await integration.send_alert({})

        body = client.post.await_args.kwargs["json"]
        assert body["name"] == "Goblin Assistant Alert"
        assert body["options"]["thresholds"] == {"critical": 50, "warning": 70}


# ---------------------------------------------------------------------------
# Prometheus
# ---------------------------------------------------------------------------


class TestPrometheusMetrics:
    @pytest.mark.asyncio
    async def test_refuses_to_send_when_disabled(self):
        assert await PrometheusIntegration().send_metrics(_METRICS) is False

    @pytest.mark.asyncio
    async def test_posts_the_exposition_text(self):
        integration = await _enabled_prometheus()
        client = _client(_Resp(200))

        with patch("httpx.AsyncClient", return_value=client):
            assert await integration.send_metrics(_METRICS) is True

        assert client.post.await_args.kwargs["headers"]["Content-Type"] == "text/plain"
        assert "goblin_assistant_system_health_score" in client.post.await_args.kwargs["data"]

    @pytest.mark.asyncio
    async def test_non_200_is_a_failure(self):
        integration = await _enabled_prometheus()

        with patch("httpx.AsyncClient", return_value=_client(_Resp(500, "boom"))):
            assert await integration.send_metrics(_METRICS) is False

    @pytest.mark.asyncio
    async def test_errors_are_swallowed(self):
        integration = await _enabled_prometheus()

        with patch("httpx.AsyncClient", side_effect=RuntimeError("offline")):
            assert await integration.send_metrics(_METRICS) is False

    def test_exposition_includes_help_and_type_for_each_metric(self):
        text = PrometheusIntegration()._transform_to_prometheus_format(_METRICS)

        assert "# HELP goblin_assistant_system_health_score" in text
        assert "# TYPE goblin_assistant_system_health_score gauge" in text
        assert "# TYPE goblin_assistant_provider_latency_ms gauge" in text

    def test_exposition_labels_each_provider(self):
        text = PrometheusIntegration()._transform_to_prometheus_format(_METRICS)

        assert 'provider="openai"' in text
        assert 'provider="groq"' in text

    def test_exposition_maps_status_to_numbers(self):
        text = PrometheusIntegration()._transform_to_prometheus_format(
            {"providers": {"p": {"status": "degraded"}}}
        )

        status_line = next(
            line
            for line in text.splitlines()
            if line.startswith("goblin_assistant_provider_status{")
        )
        assert " 0.5 " in status_line

    def test_exposition_includes_performance_and_streaming(self):
        text = PrometheusIntegration()._transform_to_prometheus_format(_METRICS)

        assert "goblin_assistant_performance_p95_ms" in text
        assert "goblin_assistant_streaming_ttfb_ms" in text

    def test_exposition_of_empty_metrics_is_empty(self):
        assert PrometheusIntegration()._transform_to_prometheus_format({}) == ""


# ---------------------------------------------------------------------------
# AlertManager
# ---------------------------------------------------------------------------


class TestAlertManagerAlerts:
    @pytest.mark.asyncio
    async def test_refuses_to_send_when_disabled(self):
        assert await AlertManagerIntegration().send_alert({"title": "x"}) is False

    @pytest.mark.asyncio
    async def test_posts_a_single_element_list(self):
        integration = await _enabled_alertmanager()
        client = _client(_Resp(200))

        with patch("httpx.AsyncClient", return_value=client):
            assert await integration.send_alert({"title": "Down"}) is True

        url = client.post.await_args.args[0]
        payload = client.post.await_args.kwargs["json"]
        assert url == "http://am.example/api/v1/alerts"
        assert isinstance(payload, list) and len(payload) == 1

    @pytest.mark.asyncio
    async def test_non_200_is_a_failure(self):
        integration = await _enabled_alertmanager()

        with patch("httpx.AsyncClient", return_value=_client(_Resp(503, "down"))):
            assert await integration.send_alert({"title": "Down"}) is False

    @pytest.mark.asyncio
    async def test_errors_are_swallowed(self):
        integration = await _enabled_alertmanager()

        with patch("httpx.AsyncClient", side_effect=RuntimeError("offline")):
            assert await integration.send_alert({"title": "Down"}) is False

    def test_transform_maps_fields_to_labels_and_annotations(self):
        alert = {
            "title": "HighLatency",
            "severity": "critical",
            "environment": "prod",
            "instance": "api-1",
            "summary": "p95 too high",
            "message": "details",
            "runbook_url": "http://rb",
            "generator_url": "http://gen",
        }

        payload = AlertManagerIntegration()._transform_to_alertmanager_format(alert)

        assert payload["labels"]["alertname"] == "HighLatency"
        assert payload["labels"]["severity"] == "critical"
        assert payload["labels"]["service"] == "goblin-assistant"
        assert payload["annotations"]["summary"] == "p95 too high"
        assert payload["annotations"]["description"] == "details"
        assert payload["generatorURL"] == "http://gen"

    def test_transform_supplies_defaults(self):
        payload = AlertManagerIntegration()._transform_to_alertmanager_format({})

        assert payload["labels"]["alertname"] == "GoblinAssistantAlert"
        assert payload["labels"]["severity"] == "warning"
        assert payload["annotations"]["summary"] == ""

    def test_transform_window_ends_after_it_starts(self):
        payload = AlertManagerIntegration()._transform_to_alertmanager_format({})

        assert payload["endsAt"] > payload["startsAt"]

    def test_transform_honours_explicit_timestamps(self):
        payload = AlertManagerIntegration()._transform_to_alertmanager_format(
            {"starts_at": "2020-01-01T00:00:00", "ends_at": "2020-01-02T00:00:00"}
        )

        assert payload["startsAt"] == "2020-01-01T00:00:00"
        assert payload["endsAt"] == "2020-01-02T00:00:00"
