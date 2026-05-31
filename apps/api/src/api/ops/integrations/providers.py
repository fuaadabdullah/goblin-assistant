"""Provider-specific monitoring integrations."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

import httpx

from .base import MonitoringIntegration

logger = logging.getLogger(__name__)


class DataDogIntegration(MonitoringIntegration):
    def __init__(self):
        super().__init__("datadog")
        self.api_key = None
        self.app_key = None
        self.base_url = "https://api.datadoghq.com/api/v1"

    async def initialize(self, config: Dict[str, Any]) -> bool:
        if not await super().initialize(config):
            return False
        self.api_key = config.get("api_key")
        self.app_key = config.get("app_key")
        if not self.api_key or not self.app_key:
            logger.warning("DataDog integration missing API key or app key")
            return False
        logger.info("DataDog integration initialized successfully")
        return True

    async def send_metrics(self, metrics: Dict[str, Any]) -> bool:
        if not self.enabled:
            return False
        try:
            datadog_metrics = self._transform_to_datadog_format(metrics)
            headers = {
                "DD-API-KEY": self.api_key,
                "DD-APPLICATION-KEY": self.app_key,
                "Content-Type": "application/json",
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/series",
                    headers=headers,
                    json={"series": datadog_metrics},
                )
                if response.status_code == 202:
                    logger.info("Successfully sent metrics to DataDog")
                    return True
                logger.error("Failed to send metrics to DataDog: %s", response.text)
                return False
        except Exception as e:
            logger.error("Error sending metrics to DataDog: %s", e)
            return False

    def _transform_to_datadog_format(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        datadog_metrics = []
        timestamp = int(datetime.utcnow().timestamp())
        health = metrics.get("health", {})
        if health:
            datadog_metrics.append(
                {
                    "metric": "goblin.assistant.system.health_score",
                    "points": [[timestamp, health.get("overall_score", 0)]],
                    "tags": [
                        "service:goblin-assistant",
                        f"environment:{metrics.get('environment', 'unknown')}",
                    ],
                }
            )

        providers = metrics.get("providers", {})
        for provider_name, provider_data in providers.items():
            tags = [
                "service:goblin-assistant",
                f"provider:{provider_name}",
                f"environment:{metrics.get('environment', 'unknown')}",
            ]
            datadog_metrics.append(
                {
                    "metric": "goblin.assistant.provider.health_score",
                    "points": [[timestamp, provider_data.get("health_score", 0)]],
                    "tags": tags,
                }
            )
            datadog_metrics.append(
                {
                    "metric": "goblin.assistant.provider.latency_ms",
                    "points": [[timestamp, provider_data.get("latency_ms", 0)]],
                    "tags": tags,
                }
            )
            status_map = {"healthy": 1, "degraded": 0.5, "critical": 0}
            status_value = status_map.get(provider_data.get("status", "unknown"), 0)
            datadog_metrics.append(
                {
                    "metric": "goblin.assistant.provider.status",
                    "points": [[timestamp, status_value]],
                    "tags": tags,
                }
            )

        performance = metrics.get("performance", {})
        if performance:
            perf_data = performance.get("aggregated", {})
            tags = [
                "service:goblin-assistant",
                f"environment:{metrics.get('environment', 'unknown')}",
            ]
            for metric_name, value in perf_data.items():
                datadog_metrics.append(
                    {
                        "metric": f"goblin.assistant.performance.{metric_name}",
                        "points": [[timestamp, value]],
                        "tags": tags,
                    }
                )

        streaming = metrics.get("streaming", {})
        if streaming:
            tags = [
                "service:goblin-assistant",
                f"environment:{metrics.get('environment', 'unknown')}",
            ]
            comparison = streaming.get("comparison", {})
            for metric_name, value in comparison.items():
                datadog_metrics.append(
                    {
                        "metric": f"goblin.assistant.streaming.{metric_name}",
                        "points": [[timestamp, value]],
                        "tags": tags,
                    }
                )

        return datadog_metrics

    async def send_alert(self, alert: Dict[str, Any]) -> bool:
        if not self.enabled:
            return False
        try:
            monitor_data = {
                "name": alert.get("title", "Goblin Assistant Alert"),
                "type": "metric alert",
                "query": alert.get(
                    "query",
                    "avg(last_5m):avg:goblin.assistant.system.health_score{*} < 50",
                ),
                "message": alert.get("message", "System health is degraded"),
                "tags": ["service:goblin-assistant"],
                "options": {
                    "notify_audit": True,
                    "notify_no_data": False,
                    "no_data_timeframe": 10,
                    "timeout_h": 24,
                    "escalation_message": "Alert is still active",
                    "thresholds": {"critical": 50, "warning": 70},
                },
            }
            headers = {
                "DD-API-KEY": self.api_key,
                "DD-APPLICATION-KEY": self.app_key,
                "Content-Type": "application/json",
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/monitor", headers=headers, json=monitor_data
                )
                if response.status_code in [200, 201]:
                    logger.info("Successfully created DataDog monitor")
                    return True
                logger.error("Failed to create DataDog monitor: %s", response.text)
                return False
        except Exception as e:
            logger.error("Error creating DataDog monitor: %s", e)
            return False


class PrometheusIntegration(MonitoringIntegration):
    def __init__(self):
        super().__init__("prometheus")
        self.metrics_endpoint = None

    async def initialize(self, config: Dict[str, Any]) -> bool:
        if not await super().initialize(config):
            return False
        self.metrics_endpoint = config.get("metrics_endpoint")
        if not self.metrics_endpoint:
            logger.warning("Prometheus integration missing metrics endpoint")
            return False
        logger.info("Prometheus integration initialized successfully")
        return True

    async def send_metrics(self, metrics: Dict[str, Any]) -> bool:
        if not self.enabled:
            return False
        try:
            prometheus_metrics = self._transform_to_prometheus_format(metrics)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.metrics_endpoint,
                    headers={"Content-Type": "text/plain"},
                    data=prometheus_metrics,
                )
                if response.status_code == 200:
                    logger.info("Successfully sent metrics to Prometheus")
                    return True
                logger.error("Failed to send metrics to Prometheus: %s", response.text)
                return False
        except Exception as e:
            logger.error("Error sending metrics to Prometheus: %s", e)
            return False

    def _transform_to_prometheus_format(self, metrics: Dict[str, Any]) -> str:
        lines = []
        timestamp = int(datetime.utcnow().timestamp())
        health = metrics.get("health", {})
        if health:
            lines.append(
                "# HELP goblin_assistant_system_health_score Goblin Assistant system health score"
            )
            lines.append("# TYPE goblin_assistant_system_health_score gauge")
            lines.append(
                f'goblin_assistant_system_health_score{{service="goblin-assistant",environment="{metrics.get("environment", "unknown")}"}} {health.get("overall_score", 0)} {timestamp}'
            )

        providers = metrics.get("providers", {})
        for provider_name, provider_data in providers.items():
            lines.append(
                "# HELP goblin_assistant_provider_health_score Goblin Assistant provider health score"
            )
            lines.append("# TYPE goblin_assistant_provider_health_score gauge")
            lines.append(
                f'goblin_assistant_provider_health_score{{service="goblin-assistant",provider="{provider_name}",environment="{metrics.get("environment", "unknown")}"}} {provider_data.get("health_score", 0)} {timestamp}'
            )
            lines.append(
                "# HELP goblin_assistant_provider_latency_ms Goblin Assistant provider latency in milliseconds"
            )
            lines.append("# TYPE goblin_assistant_provider_latency_ms gauge")
            lines.append(
                f'goblin_assistant_provider_latency_ms{{service="goblin-assistant",provider="{provider_name}",environment="{metrics.get("environment", "unknown")}"}} {provider_data.get("latency_ms", 0)} {timestamp}'
            )
            status_map = {"healthy": 1, "degraded": 0.5, "critical": 0}
            status_value = status_map.get(provider_data.get("status", "unknown"), 0)
            lines.append(
                "# HELP goblin_assistant_provider_status Goblin Assistant provider status (1=healthy, 0.5=degraded, 0=critical)"
            )
            lines.append("# TYPE goblin_assistant_provider_status gauge")
            lines.append(
                f'goblin_assistant_provider_status{{service="goblin-assistant",provider="{provider_name}",environment="{metrics.get("environment", "unknown")}"}} {status_value} {timestamp}'
            )

        performance = metrics.get("performance", {})
        if performance:
            perf_data = performance.get("aggregated", {})
            for metric_name, value in perf_data.items():
                metric_name_clean = metric_name.replace("_", "_")
                lines.append(
                    f"# HELP goblin_assistant_performance_{metric_name_clean} Goblin Assistant performance metric: {metric_name}"
                )
                lines.append(f"# TYPE goblin_assistant_performance_{metric_name_clean} gauge")
                lines.append(
                    f'goblin_assistant_performance_{metric_name_clean}{{service="goblin-assistant",environment="{metrics.get("environment", "unknown")}"}} {value} {timestamp}'
                )

        streaming = metrics.get("streaming", {})
        if streaming:
            comparison = streaming.get("comparison", {})
            for metric_name, value in comparison.items():
                metric_name_clean = metric_name.replace("_", "_")
                lines.append(
                    f"# HELP goblin_assistant_streaming_{metric_name_clean} Goblin Assistant streaming metric: {metric_name}"
                )
                lines.append(f"# TYPE goblin_assistant_streaming_{metric_name_clean} gauge")
                lines.append(
                    f'goblin_assistant_streaming_{metric_name_clean}{{service="goblin-assistant",environment="{metrics.get("environment", "unknown")}"}} {value} {timestamp}'
                )

        return "\n".join(lines)


class AlertManagerIntegration(MonitoringIntegration):
    def __init__(self):
        super().__init__("alertmanager")
        self.alertmanager_url = None

    async def initialize(self, config: Dict[str, Any]) -> bool:
        if not await super().initialize(config):
            return False
        self.alertmanager_url = config.get("alertmanager_url")
        if not self.alertmanager_url:
            logger.warning("AlertManager integration missing alertmanager_url")
            return False
        logger.info("AlertManager integration initialized successfully")
        return True

    async def send_alert(self, alert: Dict[str, Any]) -> bool:
        if not self.enabled:
            return False
        try:
            alertmanager_alert = self._transform_to_alertmanager_format(alert)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.alertmanager_url}/api/v1/alerts", json=[alertmanager_alert]
                )
                if response.status_code == 200:
                    logger.info("Successfully sent alert to AlertManager")
                    return True
                logger.error("Failed to send alert to AlertManager: %s", response.text)
                return False
        except Exception as e:
            logger.error("Error sending alert to AlertManager: %s", e)
            return False

    def _transform_to_alertmanager_format(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "labels": {
                "alertname": alert.get("title", "GoblinAssistantAlert"),
                "service": "goblin-assistant",
                "severity": alert.get("severity", "warning"),
                "environment": alert.get("environment", "unknown"),
                "instance": alert.get("instance", "unknown"),
            },
            "annotations": {
                "summary": alert.get("summary", ""),
                "description": alert.get("message", ""),
                "runbook_url": alert.get("runbook_url", ""),
            },
            "startsAt": alert.get("starts_at", datetime.utcnow().isoformat()),
            "endsAt": alert.get("ends_at", (datetime.utcnow() + timedelta(hours=1)).isoformat()),
            "generatorURL": alert.get("generator_url", ""),
        }
