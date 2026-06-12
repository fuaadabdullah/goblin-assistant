from datetime import datetime

from api.ops.audit import AuditEvent, AuditEventType, AuditSeverity


def test_audit_event_round_trip_dict() -> None:
    event = AuditEvent(
        event_id="evt_1",
        timestamp=datetime.utcnow(),
        event_type=AuditEventType.SYSTEM,
        severity=AuditSeverity.MEDIUM,
        user="tester",
        action="read",
        resource="/ops/health",
        success=True,
        client_ip="127.0.0.1",
        user_agent="pytest",
        environment="test",
        details={"foo": "bar"},
    )

    serialized = event.to_dict()
    restored = AuditEvent.from_dict(serialized)

    assert restored.event_id == event.event_id
    assert restored.event_type == event.event_type
    assert restored.severity == event.severity
    assert restored.details == event.details
