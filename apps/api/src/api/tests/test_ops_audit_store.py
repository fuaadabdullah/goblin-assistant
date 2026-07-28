import pytest

from api.ops.audit import AuditEventType, AuditSeverity, audit_logger


@pytest.mark.asyncio
async def test_audit_compliance_and_summary(monkeypatch) -> None:
    state = {}

    async def fake_get(key):
        return state.get(key)

    async def fake_set(key, value, expire=None):
        state[key] = value

    monkeypatch.setattr("api.ops.audit.storage.cache.get", fake_get)
    monkeypatch.setattr("api.ops.audit.storage.cache.set", fake_set)

    event_id = await audit_logger.log_event(
        event_type=AuditEventType.SYSTEM,
        severity=AuditSeverity.LOW,
        user="tester",
        action="health_check",
        resource="/ops/health/summary",
        success=True,
        client_ip="127.0.0.1",
        user_agent="pytest",
        environment="test",
        details={"ok": True},
    )

    assert event_id is not None

    compliance = await audit_logger.get_compliance_report()
    summary = await audit_logger.get_summary()

    assert compliance["summary"]["total_events"] == 1
    assert summary["total_events"] == 1
    assert summary["unique_users"] == 1
