"""Tests for ops route error details."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.ops_routes.circuit_breakers import circuit_breakers_status, reset_circuit_breaker
from api.ops_routes.security_audit import get_audit_log, get_security_status


@pytest.fixture(autouse=True)
def _disable_ops_auth(monkeypatch):
    monkeypatch.setattr("api.ops.security.OpsSecurityConfig.REQUIRE_AUTH", False)
    monkeypatch.setattr("api.ops.security.OpsSecurityConfig.ENVIRONMENT", "development")
    monkeypatch.setattr(
        "api.ops.security.OpsSecurityConfig.OPS_ALLOWED_ENVIRONMENTS", ["development"]
    )
    monkeypatch.setattr(
        "api.ops.security.ops_security.check_rate_limit", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        "api.ops.security.ops_security.check_environment_access", AsyncMock(return_value=True)
    )
    monkeypatch.setattr("api.ops.security.ops_security.log_audit_event", AsyncMock())
    yield


def _request() -> SimpleNamespace:
    return SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        headers={"user-agent": "pytest"},
    )


@pytest.mark.asyncio
async def test_circuit_breaker_status_error_detail():
    broken_cb = MagicMock()
    broken_cb.state = "OPEN"
    broken_cb.get_status.side_effect = Exception("boom")

    with patch("api.ops_routes.circuit_breakers.circuit_breakers", {"broken": broken_cb}):
        with pytest.raises(Exception) as exc:
            await circuit_breakers_status()

    assert exc.value.status_code == 500
    assert exc.value.detail == "Circuit breaker status failed: boom"


@pytest.mark.asyncio
async def test_circuit_breaker_reset_error_detail():
    with patch("api.ops_routes.circuit_breakers.CircuitBreaker", side_effect=Exception("boom")):
        with pytest.raises(Exception) as exc:
            await reset_circuit_breaker(_request(), "provider-x")

    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to reset circuit breaker: boom"


@pytest.mark.asyncio
async def test_security_status_error_detail():
    with patch("api.ops_routes.security_audit.get_security_summary", side_effect=Exception("boom")):
        with pytest.raises(Exception) as exc:
            await get_security_status(_request())

    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to get security status: boom"


@pytest.mark.asyncio
async def test_audit_log_error_detail():
    with patch("api.ops_routes.security_audit.get_ops_audit_log", side_effect=Exception("boom")):
        with pytest.raises(Exception) as exc:
            await get_audit_log(_request())

    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to get audit log: boom"
