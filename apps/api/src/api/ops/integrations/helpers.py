"""High-level helper functions for monitoring integrations."""

import logging
from typing import Any, Dict

from ..aggregator import aggregator
from .manager import MonitoringManager

logger = logging.getLogger(__name__)

monitoring_manager = MonitoringManager()


async def initialize_monitoring(config: Dict[str, Any]):
    await monitoring_manager.initialize(config)


async def send_system_metrics():
    try:
        await aggregator.initialize()
        metrics = await aggregator.aggregate_system_metrics()
        results = await monitoring_manager.send_metrics(metrics)
        success_count = sum(1 for success in results.values() if success)
        logger.info(f"Sent metrics to {success_count}/{len(results)} monitoring integrations")
        return results
    except Exception as e:
        logger.error(f"Failed to send system metrics: {e}")
        return {}


async def send_system_alert(alert_data: Dict[str, Any]):
    try:
        results = await monitoring_manager.send_alert(alert_data)
        success_count = sum(1 for success in results.values() if success)
        logger.info(f"Sent alert to {success_count}/{len(results)} monitoring integrations")
        return results
    except Exception as e:
        logger.error(f"Failed to send system alert: {e}")
        return {}


async def get_monitoring_status() -> Dict[str, Any]:
    return await monitoring_manager.get_status()


async def send_health_alert(health_score: float, threshold: float = 70.0):
    if health_score < threshold:
        alert = {
            "title": "System Health Degraded",
            "severity": "critical" if health_score < 50 else "warning",
            "message": f"System health score is {health_score}, below threshold of {threshold}",
            "environment": "production",
            "instance": "goblin-assistant",
            "summary": "System health is degraded",
            "runbook_url": "https://docs.goblinassistant.com/runbooks/health-degraded",
            "generator_url": "https://goblin-assistant.com/ops/health",
        }
        return await send_system_alert(alert)
    return {}


async def send_provider_alert(provider_name: str, status: str, latency: float):
    if status != "healthy":
        alert = {
            "title": f"Provider {provider_name} Unhealthy",
            "severity": "critical" if status == "critical" else "warning",
            "message": f"Provider {provider_name} is {status} with latency {latency}ms",
            "environment": "production",
            "instance": provider_name,
            "summary": f"Provider {provider_name} health issue",
            "runbook_url": f"https://docs.goblinassistant.com/runbooks/provider-{provider_name}",
            "generator_url": f"https://goblin-assistant.com/ops/providers/{provider_name}",
        }
        return await send_system_alert(alert)
    return {}


async def send_circuit_breaker_alert(provider_name: str, state: str):
    if state == "OPEN":
        alert = {
            "title": f"Circuit Breaker Open for {provider_name}",
            "severity": "warning",
            "message": f"Circuit breaker for {provider_name} is OPEN",
            "environment": "production",
            "instance": provider_name,
            "summary": f"Circuit breaker protection activated for {provider_name}",
            "runbook_url": "https://docs.goblinassistant.com/runbooks/circuit-breaker-open",
            "generator_url": f"https://goblin-assistant.com/ops/circuit-breakers/{provider_name}",
        }
        return await send_system_alert(alert)
    return {}
