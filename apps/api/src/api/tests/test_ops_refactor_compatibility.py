from api.ops.audit import (
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    audit_logger,
    get_audit_summary,
    log_ops_event,
)
from api.ops.integrations import (
    DataDogIntegration,
    MonitoringManager,
    get_monitoring_status,
    initialize_monitoring,
    monitoring_manager,
    send_circuit_breaker_alert,
    send_health_alert,
    send_provider_alert,
    send_system_alert,
    send_system_metrics,
)


def test_legacy_audit_import_surface_available() -> None:
    assert AuditEvent is not None
    assert AuditEventType is not None
    assert AuditSeverity is not None
    assert audit_logger is not None
    assert callable(log_ops_event)
    assert callable(get_audit_summary)


def test_legacy_integrations_import_surface_available() -> None:
    assert DataDogIntegration is not None
    assert MonitoringManager is not None
    assert monitoring_manager is not None
    assert callable(initialize_monitoring)
    assert callable(send_system_metrics)
    assert callable(send_system_alert)
    assert callable(get_monitoring_status)
    assert callable(send_health_alert)
    assert callable(send_provider_alert)
    assert callable(send_circuit_breaker_alert)
