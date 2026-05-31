"""Monitoring integration orchestration."""

import logging
from typing import Any, Dict

from .base import MonitoringIntegration
from .providers import (
    AlertManagerIntegration,
    DataDogIntegration,
    PrometheusIntegration,
)

logger = logging.getLogger(__name__)


class MonitoringManager:
    """Manager for all monitoring integrations."""

    def __init__(self):
        self.integrations: Dict[str, MonitoringIntegration] = {}
        self.config = {}

    async def initialize(self, config: Dict[str, Any]):
        self.config = config
        if "datadog" in config:
            datadog = DataDogIntegration()
            await datadog.initialize(config["datadog"])
            self.integrations["datadog"] = datadog
        if "prometheus" in config:
            prometheus = PrometheusIntegration()
            await prometheus.initialize(config["prometheus"])
            self.integrations["prometheus"] = prometheus
        if "alertmanager" in config:
            alertmanager = AlertManagerIntegration()
            await alertmanager.initialize(config["alertmanager"])
            self.integrations["alertmanager"] = alertmanager
        logger.info("Initialized %s monitoring integrations", len(self.integrations))

    async def send_metrics(self, metrics: Dict[str, Any]):
        results = {}
        for name, integration in self.integrations.items():
            try:
                success = await integration.send_metrics(metrics)
                results[name] = success
                if success:
                    logger.info("Successfully sent metrics to %s", name)
                else:
                    logger.warning("Failed to send metrics to %s", name)
            except Exception as e:
                logger.error("Error sending metrics to %s: %s", name, e)
                results[name] = False
        return results

    async def send_alert(self, alert: Dict[str, Any]):
        results = {}
        for name, integration in self.integrations.items():
            try:
                if hasattr(integration, "send_alert"):
                    success = await integration.send_alert(alert)
                    results[name] = success
                    if success:
                        logger.info("Successfully sent alert to %s", name)
                    else:
                        logger.warning("Failed to send alert to %s", name)
            except Exception as e:
                logger.error("Error sending alert to %s: %s", name, e)
                results[name] = False
        return results

    async def get_status(self) -> Dict[str, Any]:
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
