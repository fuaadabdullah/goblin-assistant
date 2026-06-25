"""External Monitoring System Integrations.

This package supersedes the previous monolithic module layout and retains
legacy import compatibility at `api.ops.integrations`.
"""

import os

from .base import MonitoringIntegration
from .helpers import (
    get_monitoring_status,
    initialize_monitoring,
    monitoring_manager,
    send_circuit_breaker_alert,
    send_health_alert,
    send_provider_alert,
    send_system_alert,
    send_system_metrics,
)
from .jira import (
    build_circuit_breaker_incident_payload,
    build_provider_health_incident_payload,
    jira_incident_dedupe_key,
    jira_provider_ops_enabled,
    post_jira_provider_ops_payload,
    publish_circuit_breaker_incident,
    publish_provider_health_incident,
)
from .manager import MonitoringManager
from .providers import (
    AlertManagerIntegration,
    DataDogIntegration,
    PrometheusIntegration,
)

_DEPRECATION_WARN_ENV = "OPS_INTEGRATIONS_IMPORT_DEPRECATION_WARN"

if os.getenv(_DEPRECATION_WARN_ENV, "false").lower() in {"1", "true", "yes", "on"}:
    import warnings

    warnings.warn(
        "`api.ops.integrations` now uses a package-based implementation. "
        "Prefer submodule imports such as `api.ops.integrations.manager` and `api.ops.integrations.providers`.",
        DeprecationWarning,
        stacklevel=2,
    )


__all__ = [
    "AlertManagerIntegration",
    "DataDogIntegration",
    "MonitoringIntegration",
    "MonitoringManager",
    "PrometheusIntegration",
    "build_circuit_breaker_incident_payload",
    "build_provider_health_incident_payload",
    "get_monitoring_status",
    "initialize_monitoring",
    "jira_incident_dedupe_key",
    "jira_provider_ops_enabled",
    "monitoring_manager",
    "post_jira_provider_ops_payload",
    "publish_circuit_breaker_incident",
    "publish_provider_health_incident",
    "send_circuit_breaker_alert",
    "send_health_alert",
    "send_provider_alert",
    "send_system_alert",
    "send_system_metrics",
]
