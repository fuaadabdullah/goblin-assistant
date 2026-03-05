"""
External Monitoring System Integrations
Integrates with DataDog, Prometheus, and other monitoring systems
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import httpx
from dataclasses import asdict

from ..storage.cache import cache
from ..config.redis_config import redis_config
from .aggregator import aggregator
from .audit import audit_logger, AuditEventType, AuditSeverity

logger = logging.getLogger(__name__)


class MonitoringIntegration:
    """Base class for monitoring system integrations"""

    def __init__(self, name: str):
        self.name = name
        self.enabled = False
        self.config = {}

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the integration with configuration"""
        self.config = config
        self.enabled = config.get("enabled", False)
        return self.enabled

    async def send_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Send metrics to the monitoring system"""
        raise NotImplementedError

    async def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Send alert to the monitoring system"""
        raise NotImplementedError


class DataDogIntegration(MonitoringIntegration):
    """DataDog monitoring integration"""

    def __init__(self):
        super().__init__("datadog")
        self.api_key = None
        self.app_key = None
        self.base_url = "https://api.datadoghq.com/api/v1"

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize DataDog integration"""
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
        """Send metrics to DataDog"""
        if not self.enabled:
            return False

        try:
            # Transform metrics to DataDog format
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
                else:
                    logger.error(f"Failed to send metrics to DataDog: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Error sending metrics to DataDog: {e}")
            return False

    def _transform_to_datadog_format(
        self, metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Transform our metrics to DataDog format"""
        datadog_metrics = []
        timestamp = int(datetime.utcnow().timestamp())

        # System health metrics
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

        # Provider metrics
        providers = metrics.get("providers", {})
        for provider_name, provider_data in providers.items():
            tags = [
                f"service:goblin-assistant",
                f"provider:{provider_name}",
                f"environment:{metrics.get('environment', 'unknown')}",
            ]

            # Health score
            datadog_metrics.append(
                {
                    "metric": "goblin.assistant.provider.health_score",
                    "points": [[timestamp, provider_data.get("health_score", 0)]],
                    "tags": tags,
                }
            )

            # Latency
            datadog_metrics.append(
                {
                    "metric": "goblin.assistant.provider.latency_ms",
                    "points": [[timestamp, provider_data.get("latency_ms", 0)]],
                    "tags": tags,
                }
            )

            # Status (convert to numeric)
            status_map = {"healthy": 1, "degraded": 0.5, "critical": 0}
            status_value = status_map.get(provider_data.get("status", "unknown"), 0)
            datadog_metrics.append(
                {
                    "metric": "goblin.assistant.provider.status",
                    "points": [[timestamp, status_value]],
                    "tags": tags,
                }
            )

        # Performance metrics
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

        # Streaming metrics
        streaming = metrics.get("streaming", {})
        if streaming:
            tags = [
                "service:goblin-assistant",
                f"environment:{metrics.get('environment', 'unknown')}",
            ]

            # Streaming vs non-streaming comparison
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
        """Send alert to DataDog"""
        if not self.enabled:
            return False

        try:
            # Create DataDog monitor
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
                else:
                    logger.error(f"Failed to create DataDog monitor: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Error creating DataDog monitor: {e}")
            return False


class PrometheusIntegration(MonitoringIntegration):
    """Prometheus monitoring integration"""

    def __init__(self):
        super().__init__("prometheus")
        self.metrics_endpoint = None

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize Prometheus integration"""
        if not await super().initialize(config):
            return False

        self.metrics_endpoint = config.get("metrics_endpoint")
        if not self.metrics_endpoint:
            logger.warning("Prometheus integration missing metrics endpoint")
            return False

        logger.info("Prometheus integration initialized successfully")
        return True

    async def send_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Send metrics to Prometheus pushgateway"""
        if not self.enabled:
            return False

        try:
            # Transform metrics to Prometheus format
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
                else:
                    logger.error(
                        f"Failed to send metrics to Prometheus: {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error sending metrics to Prometheus: {e}")
            return False

    def _transform_to_prometheus_format(self, metrics: Dict[str, Any]) -> str:
        """Transform our metrics to Prometheus format"""
        lines = []
        timestamp = int(datetime.utcnow().timestamp())

        # System health metrics
        health = metrics.get("health", {})
        if health:
            lines.append(
                f"# HELP goblin_assistant_system_health_score Goblin Assistant system health score"
            )
            lines.append(f"# TYPE goblin_assistant_system_health_score gauge")
            lines.append(
                f'goblin_assistant_system_health_score{{service="goblin-assistant",environment="{metrics.get("environment", "unknown")}"}} {health.get("overall_score", 0)} {timestamp}'
            )

        # Provider metrics
        providers = metrics.get("providers", {})
        for provider_name, provider_data in providers.items():
            # Health score
            lines.append(
                f"# HELP goblin_assistant_provider_health_score Goblin Assistant provider health score"
            )
            lines.append(f"# TYPE goblin_assistant_provider_health_score gauge")
            lines.append(
                f'goblin_assistant_provider_health_score{{service="goblin-assistant",provider="{provider_name}",environment="{metrics.get("environment", "unknown")}"}} {provider_data.get("health_score", 0)} {timestamp}'
            )

            # Latency
            lines.append(
                f"# HELP goblin_assistant_provider_latency_ms Goblin Assistant provider latency in milliseconds"
            )
            lines.append(f"# TYPE goblin_assistant_provider_latency_ms gauge")
            lines.append(
                f'goblin_assistant_provider_latency_ms{{service="goblin-assistant",provider="{provider_name}",environment="{metrics.get("environment", "unknown")}"}} {provider_data.get("latency_ms", 0)} {timestamp}'
            )

            # Status (convert to numeric)
            status_map = {"healthy": 1, "degraded": 0.5, "critical": 0}
            status_value = status_map.get(provider_data.get("status", "unknown"), 0)
            lines.append(
                f"# HELP goblin_assistant_provider_status Goblin Assistant provider status (1=healthy, 0.5=degraded, 0=critical)"
            )
            lines.append(f"# TYPE goblin_assistant_provider_status gauge")
            lines.append(
                f'goblin_assistant_provider_status{{service="goblin-assistant",provider="{provider_name}",environment="{metrics.get("environment", "unknown")}"}} {status_value} {timestamp}'
            )

        # Performance metrics
        performance = metrics.get("performance", {})
        if performance:
            perf_data = performance.get("aggregated", {})
            for metric_name, value in perf_data.items():
                metric_name_clean = metric_name.replace("_", "_")
                lines.append(
                    f"# HELP goblin_assistant_performance_{metric_name_clean} Goblin Assistant performance metric: {metric_name}"
                )
                lines.append(
                    f"# TYPE goblin_assistant_performance_{metric_name_clean} gauge"
                )
                lines.append(
                    f'goblin_assistant_performance_{metric_name_clean}{{service="goblin-assistant",environment="{metrics.get("environment", "unknown")}"}} {value} {timestamp}'
                )

        # Streaming metrics
        streaming = metrics.get("streaming", {})
        if streaming:
            comparison = streaming.get("comparison", {})
            for metric_name, value in comparison.items():
                metric_name_clean = metric_name.replace("_", "_")
                lines.append(
                    f"# HELP goblin_assistant_streaming_{metric_name_clean} Goblin Assistant streaming metric: {metric_name}"
                )
                lines.append(
                    f"# TYPE goblin_assistant_streaming_{metric_name_clean} gauge"
                )
                lines.append(
                    f'goblin_assistant_streaming_{metric_name_clean}{{service="goblin-assistant",environment="{metrics.get("environment", "unknown")}"}} {value} {timestamp}'
                )

        return "\n".join(lines)


class AlertManagerIntegration(MonitoringIntegration):
    """AlertManager integration for alert routing"""

    def __init__(self):
        super().__init__("alertmanager")
        self.alertmanager_url = None

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize AlertManager integration"""
        if not await super().initialize(config):
            return False

        self.alertmanager_url = config.get("alertmanager_url")
        if not self.alertmanager_url:
            logger.warning("AlertManager integration missing alertmanager_url")
            return False

        logger.info("AlertManager integration initialized successfully")
        return True

    async def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Send alert to AlertManager"""
        if not self.enabled:
            return False

        try:
            # Transform alert to AlertManager format
            alertmanager_alert = self._transform_to_alertmanager_format(alert)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.alertmanager_url}/api/v1/alerts", json=[alertmanager_alert]
                )

                if response.status_code == 200:
                    logger.info("Successfully sent alert to AlertManager")
                    return True
                else:
                    logger.error(
                        f"Failed to send alert to AlertManager: {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error sending alert to AlertManager: {e}")
            return False

    def _transform_to_alertmanager_format(
        self, alert: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform our alert to AlertManager format"""
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
            "endsAt": alert.get(
                "ends_at", (datetime.utcnow() + timedelta(hours=1)).isoformat()
            ),
            "generatorURL": alert.get("generator_url", ""),
        }


class MonitoringManager:
    """Manager for all monitoring integrations"""

    def __init__(self):
        self.integrations: Dict[str, MonitoringIntegration] = {}
        self.config = {}

    async def initialize(self, config: Dict[str, Any]):
        """Initialize all monitoring integrations"""
        self.config = config

        # Initialize DataDog integration
        if "datadog" in config:
            datadog = DataDogIntegration()
            await datadog.initialize(config["datadog"])
            self.integrations["datadog"] = datadog

        # Initialize Prometheus integration
        if "prometheus" in config:
            prometheus = PrometheusIntegration()
            await prometheus.initialize(config["prometheus"])
            self.integrations["prometheus"] = prometheus

        # Initialize AlertManager integration
        if "alertmanager" in config:
            alertmanager = AlertManagerIntegration()
            await alertmanager.initialize(config["alertmanager"])
            self.integrations["alertmanager"] = alertmanager

        logger.info(f"Initialized {len(self.integrations)} monitoring integrations")

    async def send_metrics(self, metrics: Dict[str, Any]):
        """Send metrics to all enabled integrations"""
        results = {}
        for name, integration in self.integrations.items():
            try:
                success = await integration.send_metrics(metrics)
                results[name] = success
                if success:
                    logger.info(f"Successfully sent metrics to {name}")
                else:
                    logger.warning(f"Failed to send metrics to {name}")
            except Exception as e:
                logger.error(f"Error sending metrics to {name}: {e}")
                results[name] = False

        return results

    async def send_alert(self, alert: Dict[str, Any]):
        """Send alert to all enabled integrations"""
        results = {}
        for name, integration in self.integrations.items():
            try:
                if hasattr(integration, "send_alert"):
                    success = await integration.send_alert(alert)
                    results[name] = success
                    if success:
                        logger.info(f"Successfully sent alert to {name}")
                    else:
                        logger.warning(f"Failed to send alert to {name}")
            except Exception as e:
                logger.error(f"Error sending alert to {name}: {e}")
                results[name] = False

        return results

    async def get_status(self) -> Dict[str, Any]:
        """Get status of all integrations"""
        status = {}
        for name, integration in self.integrations.items():
            status[name] = {
                "enabled": integration.enabled,
                "config": {
                    k: "****" if k in ["api_key", "app_key"] else v
                    for k, v in integration.config.items()
                },
            }
        return status


# Global monitoring manager instance
monitoring_manager = MonitoringManager()


async def initialize_monitoring(config: Dict[str, Any]):
    """Initialize monitoring integrations"""
    await monitoring_manager.initialize(config)


async def send_system_metrics():
    """Send current system metrics to all monitoring integrations"""
    try:
        # Get aggregated metrics
        await aggregator.initialize()
        metrics = await aggregator.aggregate_system_metrics()

        # Send to all integrations
        results = await monitoring_manager.send_metrics(metrics)

        # Log results
        success_count = sum(1 for success in results.values() if success)
        logger.info(
            f"Sent metrics to {success_count}/{len(results)} monitoring integrations"
        )

        return results

    except Exception as e:
        logger.error(f"Failed to send system metrics: {e}")
        return {}


async def send_system_alert(alert_data: Dict[str, Any]):
    """Send system alert to all monitoring integrations"""
    try:
        # Send to all integrations
        results = await monitoring_manager.send_alert(alert_data)

        # Log results
        success_count = sum(1 for success in results.values() if success)
        logger.info(
            f"Sent alert to {success_count}/{len(results)} monitoring integrations"
        )

        return results

    except Exception as e:
        logger.error(f"Failed to send system alert: {e}")
        return {}


async def get_monitoring_status() -> Dict[str, Any]:
    """Get status of all monitoring integrations"""
    return await monitoring_manager.get_status()


# Convenience functions for common alert types
async def send_health_alert(health_score: float, threshold: float = 70.0):
    """Send health alert if health score is below threshold"""
    if health_score < threshold:
        alert = {
            "title": "System Health Degraded",
            "severity": "critical" if health_score < 50 else "warning",
            "message": f"System health score is {health_score}, below threshold of {threshold}",
            "environment": "production",  # Would be dynamic
            "instance": "goblin-assistant",
            "summary": "System health is degraded",
            "runbook_url": "https://docs.goblinassistant.com/runbooks/health-degraded",
            "generator_url": "https://goblin-assistant.com/ops/health",
        }
        return await send_system_alert(alert)
    return {}


async def send_provider_alert(provider_name: str, status: str, latency: float):
    """Send provider alert for unhealthy providers"""
    if status != "healthy":
        alert = {
            "title": f"Provider {provider_name} Unhealthy",
            "severity": "critical" if status == "critical" else "warning",
            "message": f"Provider {provider_name} is {status} with latency {latency}ms",
            "environment": "production",  # Would be dynamic
            "instance": provider_name,
            "summary": f"Provider {provider_name} health issue",
            "runbook_url": f"https://docs.goblinassistant.com/runbooks/provider-{provider_name}",
            "generator_url": f"https://goblin-assistant.com/ops/providers/{provider_name}",
        }
        return await send_system_alert(alert)
    return {}


async def send_circuit_breaker_alert(provider_name: str, state: str):
    """Send circuit breaker alert"""
    if state == "OPEN":
        alert = {
            "title": f"Circuit Breaker Open for {provider_name}",
            "severity": "warning",
            "message": f"Circuit breaker for {provider_name} is OPEN",
            "environment": "production",  # Would be dynamic
            "instance": provider_name,
            "summary": f"Circuit breaker protection activated for {provider_name}",
            "runbook_url": "https://docs.goblinassistant.com/runbooks/circuit-breaker-open",
            "generator_url": f"https://goblin-assistant.com/ops/circuit-breakers/{provider_name}",
        }
        return await send_system_alert(alert)
    return {}
