"""\nAlerting System\nImplements monitoring and alerting for system health issues\n"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import structlog

from ..config.system_config import get_system_config
from .alerting_system_pkg import (
    check_alerts as _check_alerts,
)
from .alerting_system_pkg import (
    cleanup_resolved_alert as _cleanup_resolved_alert,
)
from .alerting_system_pkg import (
    create_alert as _create_alert,
)
from .alerting_system_pkg import (
    get_active_alerts as _get_active_alerts,
)
from .alerting_system_pkg import (
    get_alert_summary as _get_alert_summary,
)
from .alerting_system_pkg import (
    resolve_alert as _resolve_alert,
)
from .alerting_system_pkg import (
    start_monitoring as _start_monitoring,
)
from .metrics_collector import SystemMetrics

logger = structlog.get_logger()


class AlertSeverity(Enum):
    """Alert severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status"""

    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class Alert:
    """Alert definition"""

    alert_id: str
    timestamp: datetime
    severity: AlertSeverity
    status: AlertStatus
    title: str
    description: str
    metric_name: str
    current_value: float
    threshold_value: float
    operator: str
    user_id: Optional[str]
    metadata: Dict[str, Any]
    resolved_at: Optional[datetime] = None


class AlertingSystem:
    """System for monitoring and alerting on observability metrics"""

    Alert = Alert
    AlertSeverity = AlertSeverity
    AlertStatus = AlertStatus
    SystemMetrics = SystemMetrics
    logger = logger

    def __init__(self):
        self.config = get_system_config()
        self._alerts: Dict[str, Alert] = {}
        self._alert_callbacks: List[Callable[[Alert], None]] = []
        self._suppressed_alerts: set = set()
        self._default_thresholds = {
            "memory_promotion_rate": {
                "operator": "<",
                "value": 5,
                "severity": AlertSeverity.HIGH,
            },
            "retrieval_error_rate": {
                "operator": ">",
                "value": 10,
                "severity": AlertSeverity.HIGH,
            },
            "retrieval_avg_relevance": {
                "operator": "<",
                "value": 0.5,
                "severity": AlertSeverity.MEDIUM,
            },
            "context_assembly_time": {
                "operator": ">",
                "value": 1000,
                "severity": AlertSeverity.MEDIUM,
            },
            "decision_confidence": {
                "operator": "<",
                "value": 0.6,
                "severity": AlertSeverity.MEDIUM,
            },
            "overall_health_score": {
                "operator": "<",
                "value": 50,
                "severity": AlertSeverity.CRITICAL,
            },
        }

    async def start_monitoring(self):
        await _start_monitoring(self)

    async def _monitoring_loop(self):
        while True:
            try:
                await self._check_alerts()
                await asyncio.sleep(60)
            except Exception as e:
                self.logger.error("Error in monitoring loop:", error=str(e))
                await asyncio.sleep(60)

    async def _check_alerts(self):
        await _check_alerts(self)

    async def _check_memory_alerts(self, metrics: SystemMetrics):
        from .alerting_system_pkg.core import _check_memory_alerts as _impl

        await _impl(self, metrics)

    async def _check_retrieval_alerts(self, metrics: SystemMetrics):
        from .alerting_system_pkg.core import _check_retrieval_alerts as _impl

        await _impl(self, metrics)

    async def _check_context_alerts(self, metrics: SystemMetrics):
        from .alerting_system_pkg.core import _check_context_alerts as _impl

        await _impl(self, metrics)

    async def _check_decision_alerts(self, metrics: SystemMetrics):
        from .alerting_system_pkg.core import _check_decision_alerts as _impl

        await _impl(self, metrics)

    async def _check_overall_health_alerts(self, metrics: SystemMetrics):
        from .alerting_system_pkg.core import _check_overall_health_alerts as _impl

        await _impl(self, metrics)

    async def _create_alert(
        self,
        title: str,
        description: str,
        metric_name: str,
        current_value: float,
        threshold_value: float,
        severity: AlertSeverity,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        await _create_alert(
            self,
            title=title,
            description=description,
            metric_name=metric_name,
            current_value=current_value,
            threshold_value=threshold_value,
            severity=severity,
            user_id=user_id,
            metadata=metadata,
        )

    async def _notify_alert(self, alert: Alert):
        from .alerting_system_pkg.core import notify_alert as _impl

        await _impl(self, alert)

    def register_alert_callback(self, callback: Callable[[Alert], None]):
        self._alert_callbacks.append(callback)

    async def resolve_alert(self, alert_id: str):
        await _resolve_alert(self, alert_id)

    async def _cleanup_resolved_alert(self, alert_id: str, delay_minutes: int = 60):
        await _cleanup_resolved_alert(self, alert_id, delay_minutes)

    def suppress_alert(self, alert_id: str):
        self._suppressed_alerts.add(alert_id)
        self.logger.info("Alert suppressed:", alert_id=alert_id)

    def unsuppress_alert(self, alert_id: str):
        self._suppressed_alerts.discard(alert_id)
        self.logger.info("Alert unsuppressed:", alert_id=alert_id)

    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        return _get_active_alerts(self, severity)

    def get_alert_summary(self) -> Dict[str, Any]:
        return _get_alert_summary(self)


alerting_system = AlertingSystem()

from .alert_handlers import (  # noqa: E402 - handlers need the singleton-free types above
    email_alert_handler,
    log_alert_handler,
    slack_alert_handler,
    webhook_alert_handler,
)

alerting_system.register_alert_callback(log_alert_handler)
alerting_system.register_alert_callback(email_alert_handler)
alerting_system.register_alert_callback(webhook_alert_handler)
alerting_system.register_alert_callback(slack_alert_handler)
