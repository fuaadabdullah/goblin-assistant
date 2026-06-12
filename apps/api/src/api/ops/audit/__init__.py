"""Comprehensive Audit Logging System for Operational Endpoints.

This package supersedes the previous monolithic module layout and retains
legacy import compatibility at `api.ops.audit`.
"""

import os

from .models import AuditEvent, AuditEventType, AuditSeverity
from .service import AuditLogger

_DEPRECATION_WARN_ENV = "OPS_AUDIT_IMPORT_DEPRECATION_WARN"

if os.getenv(_DEPRECATION_WARN_ENV, "false").lower() in {"1", "true", "yes", "on"}:
    import warnings

    warnings.warn(
        "`api.ops.audit` now uses a package-based implementation. "
        "Prefer submodule imports such as `api.ops.audit.models` and `api.ops.audit.service`.",
        DeprecationWarning,
        stacklevel=2,
    )


audit_logger = AuditLogger()


async def log_ops_event(
    event_type: AuditEventType,
    severity: AuditSeverity,
    user: str,
    action: str,
    resource: str,
    success: bool,
    client_ip: str = "unknown",
    user_agent: str = "unknown",
    environment: str = "unknown",
    details=None,
    session_id: str = None,
    request_id: str = None,
    response_time_ms: float = None,
    error_message: str = None,
):
    return await audit_logger.log_event(
        event_type=event_type,
        severity=severity,
        user=user,
        action=action,
        resource=resource,
        success=success,
        client_ip=client_ip,
        user_agent=user_agent,
        environment=environment,
        details=details,
        session_id=session_id,
        request_id=request_id,
        response_time_ms=response_time_ms,
        error_message=error_message,
    )


async def get_audit_summary():
    return await audit_logger.get_summary()


__all__ = [
    "AuditEvent",
    "AuditEventType",
    "AuditLogger",
    "AuditSeverity",
    "audit_logger",
    "get_audit_summary",
    "log_ops_event",
]
