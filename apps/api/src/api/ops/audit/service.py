"""High-level audit logger service."""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from .models import AuditEvent, AuditEventType, AuditSeverity
from .storage import AuditStore

logger = logging.getLogger(__name__)


class AuditLogger:
    """Advanced audit logging system with analysis and compliance features."""

    def __init__(self):
        self.audit_log_key = "ops_audit_log_v2"
        self.compliance_key = "ops_compliance_report"
        self.alerts_key = "ops_security_alerts"
        self.session_cache = {}
        self._store = AuditStore(
            audit_log_key=self.audit_log_key,
            compliance_key=self.compliance_key,
            alerts_key=self.alerts_key,
        )

    async def log_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        user: str,
        action: str,
        resource: str,
        success: bool,
        client_ip: str,
        user_agent: str,
        environment: str,
        details: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        response_time_ms: Optional[float] = None,
        error_message: Optional[str] = None,
    ) -> Optional[str]:
        try:
            event = AuditEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                event_type=event_type,
                severity=severity,
                user=user,
                action=action,
                resource=resource,
                success=success,
                client_ip=client_ip,
                user_agent=user_agent,
                environment=environment,
                details=details or {},
                session_id=session_id,
                request_id=request_id,
                response_time_ms=response_time_ms,
                error_message=error_message,
            )
            await self._store.store_event(event)
            self._log_to_console(event)
            await self._store.check_security_alerts(event)
            await self._store.update_compliance_metrics(event)
            return event.event_id
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return None

    def _log_to_console(self, event: AuditEvent) -> None:
        log_data = {
            "audit_event": True,
            "event_id": event.event_id,
            "timestamp": event.timestamp.isoformat(),
            "type": event.event_type.value,
            "severity": event.severity.value,
            "user": event.user,
            "action": event.action,
            "resource": event.resource,
            "success": event.success,
            "client_ip": event.client_ip,
            "environment": event.environment,
            "session_id": event.session_id,
            "request_id": event.request_id,
            "response_time_ms": event.response_time_ms,
            "error_message": event.error_message,
        }
        if event.success:
            logger.info(f"AUDIT: {json.dumps(log_data)}")
        else:
            logger.warning(f"AUDIT: {json.dumps(log_data)}")

    async def get_audit_log(self, limit: int = 100, offset: int = 0, filters=None):
        return await self._store.get_audit_log(limit=limit, offset=offset, filters=filters)

    async def get_security_alerts(self, limit: int = 100):
        return await self._store.get_security_alerts(limit=limit)

    async def get_compliance_report(self):
        return await self._store.get_compliance_report()

    async def search_audit_log(
        self, query: str, start_time=None, end_time=None, user=None, resource=None
    ):
        return await self._store.search_audit_log(
            query=query,
            start_time=start_time,
            end_time=end_time,
            user=user,
            resource=resource,
        )

    async def export_audit_log(self, format: str = "json", start_time=None, end_time=None):
        return await self._store.export_audit_log(
            format=format, start_time=start_time, end_time=end_time
        )

    async def get_user_activity_report(self, user: str, days: int = 30):
        return await self._store.get_user_activity_report(user=user, days=days)

    async def get_summary(self):
        return await self._store.get_summary()
