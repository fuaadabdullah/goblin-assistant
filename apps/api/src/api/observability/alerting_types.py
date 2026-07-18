"""Shared alerting contracts for alert systems and handler plugins."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class AlertSeverity(Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert lifecycle state."""

    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class Alert:
    """Alert event payload."""

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
