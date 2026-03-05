"""
Comprehensive Audit Logging System for Operational Endpoints
Provides detailed logging, analysis, and compliance reporting
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict
import hashlib
import uuid

from ..storage.cache import cache
from ..security_config import SecurityConfig

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events"""

    READ = "read"
    WRITE = "write"
    RESET = "reset"
    DEBUG = "debug"
    SECURITY = "security"
    SYSTEM = "system"


class AuditSeverity(Enum):
    """Severity levels for audit events"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Structured audit event with all necessary metadata"""

    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    severity: AuditSeverity
    user: str
    action: str
    resource: str
    success: bool
    client_ip: str
    user_agent: str
    environment: str
    details: Dict[str, Any]
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["event_type"] = self.event_type.value
        data["severity"] = self.severity.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvent":
        """Create from dictionary"""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["event_type"] = AuditEventType(data["event_type"])
        data["severity"] = AuditSeverity(data["severity"])
        return cls(**data)


class AuditLogger:
    """Advanced audit logging system with analysis and compliance features"""

    def __init__(self):
        self.audit_log_key = "ops_audit_log_v2"
        self.compliance_key = "ops_compliance_report"
        self.alerts_key = "ops_security_alerts"
        self.session_cache = {}  # Track active sessions

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
        details: Dict[str, Any] = None,
        session_id: str = None,
        request_id: str = None,
        response_time_ms: float = None,
        error_message: str = None,
    ) -> str:
        """Log an audit event with comprehensive metadata"""
        try:
            # Generate unique event ID
            event_id = str(uuid.uuid4())

            # Create audit event
            audit_event = AuditEvent(
                event_id=event_id,
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

            # Store in cache with TTL
            await self._store_event(audit_event)

            # Log to console for immediate visibility
            self._log_to_console(audit_event)

            # Check for security alerts
            await self._check_security_alerts(audit_event)

            # Update compliance metrics
            await self._update_compliance_metrics(audit_event)

            return event_id

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return None

    async def _store_event(self, event: AuditEvent):
        """Store audit event in cache with rotation"""
        try:
            # Get existing log
            audit_log = await cache.get(self.audit_log_key) or []

            # Add new event
            audit_log.append(event.to_dict())

            # Keep only last 10000 events (configurable)
            if len(audit_log) > 10000:
                audit_log = audit_log[-10000:]

            # Store with 30 day TTL
            await cache.set(self.audit_log_key, audit_log, expire=86400 * 30)

        except Exception as e:
            logger.error(f"Failed to store audit event: {e}")

    def _log_to_console(self, event: AuditEvent):
        """Log event to console with structured format"""
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

    async def _check_security_alerts(self, event: AuditEvent):
        """Check for security patterns that require alerts"""
        try:
            alerts = await cache.get(self.alerts_key) or []

            # Check for failed authentication attempts
            if not event.success and event.action in ["auth", "login", "access"]:
                alerts.append(
                    {
                        "type": "failed_authentication",
                        "user": event.user,
                        "ip": event.client_ip,
                        "timestamp": event.timestamp.isoformat(),
                        "count": 1,
                    }
                )

            # Check for suspicious activity patterns
            if event.severity == AuditSeverity.CRITICAL:
                alerts.append(
                    {
                        "type": "critical_operation",
                        "user": event.user,
                        "action": event.action,
                        "resource": event.resource,
                        "timestamp": event.timestamp.isoformat(),
                    }
                )

            # Check for circuit breaker resets in production
            if (
                event.action == "circuit_breaker_reset"
                and event.environment == "production"
                and event.severity != AuditSeverity.LOW
            ):
                alerts.append(
                    {
                        "type": "production_circuit_reset",
                        "user": event.user,
                        "ip": event.client_ip,
                        "timestamp": event.timestamp.isoformat(),
                    }
                )

            # Store alerts
            if alerts:
                await cache.set(
                    self.alerts_key, alerts[-1000:], expire=86400 * 7
                )  # Keep 7 days

        except Exception as e:
            logger.error(f"Failed to check security alerts: {e}")

    async def _update_compliance_metrics(self, event: AuditEvent):
        """Update compliance and metrics tracking"""
        try:
            compliance = await cache.get(self.compliance_key) or {
                "total_events": 0,
                "events_by_type": defaultdict(int),
                "events_by_severity": defaultdict(int),
                "events_by_user": defaultdict(int),
                "events_by_hour": defaultdict(int),
                "failed_operations": 0,
                "unique_users": set(),
                "last_updated": datetime.utcnow().isoformat(),
            }

            # Update counters
            compliance["total_events"] += 1
            compliance["events_by_type"][event.event_type.value] += 1
            compliance["events_by_severity"][event.severity.value] += 1
            compliance["events_by_user"][event.user] += 1

            # Track hourly distribution
            hour_key = event.timestamp.strftime("%Y-%m-%d %H")
            compliance["events_by_hour"][hour_key] += 1

            if not event.success:
                compliance["failed_operations"] += 1

            compliance["unique_users"].add(event.user)
            compliance["last_updated"] = datetime.utcnow().isoformat()

            # Convert set to list for JSON serialization
            compliance["unique_users"] = list(compliance["unique_users"])

            # Store with 90 day TTL
            await cache.set(self.compliance_key, compliance, expire=86400 * 90)

        except Exception as e:
            logger.error(f"Failed to update compliance metrics: {e}")

    async def get_audit_log(
        self, limit: int = 100, offset: int = 0, filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Get audit log with optional filtering and pagination"""
        try:
            audit_log = await cache.get(self.audit_log_key) or []

            # Apply filters
            if filters:
                filtered_log = []
                for event in audit_log:
                    matches = True
                    for key, value in filters.items():
                        if key not in event or event[key] != value:
                            matches = False
                            break
                    if matches:
                        filtered_log.append(event)
                audit_log = filtered_log

            # Sort by timestamp (newest first)
            audit_log.sort(key=lambda x: x["timestamp"], reverse=True)

            # Apply pagination
            start = offset
            end = offset + limit
            return audit_log[start:end]

        except Exception as e:
            logger.error(f"Failed to get audit log: {e}")
            return []

    async def get_security_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get security alerts"""
        try:
            alerts = await cache.get(self.alerts_key) or []
            return alerts[-limit:]  # Return most recent
        except Exception as e:
            logger.error(f"Failed to get security alerts: {e}")
            return []

    async def get_compliance_report(self) -> Dict[str, Any]:
        """Get compliance and usage report"""
        try:
            compliance = await cache.get(self.compliance_key) or {}

            # Calculate additional metrics
            total_events = compliance.get("total_events", 0)
            failed_operations = compliance.get("failed_operations", 0)
            failure_rate = (
                (failed_operations / total_events * 100) if total_events > 0 else 0
            )

            # Calculate activity distribution
            events_by_hour = compliance.get("events_by_hour", {})
            peak_hour = max(
                events_by_hour.items(), key=lambda x: x[1], default=("N/A", 0)
            )

            return {
                "summary": {
                    "total_events": total_events,
                    "unique_users": len(compliance.get("unique_users", [])),
                    "failure_rate": round(failure_rate, 2),
                    "peak_activity_hour": peak_hour,
                    "last_updated": compliance.get("last_updated", "N/A"),
                },
                "breakdown": {
                    "by_type": dict(compliance.get("events_by_type", {})),
                    "by_severity": dict(compliance.get("events_by_severity", {})),
                    "by_user": dict(compliance.get("events_by_user", {})),
                    "by_hour": dict(events_by_hour),
                },
                "compliance": {
                    "audit_trail_complete": total_events > 0,
                    "failed_operations_under_threshold": failure_rate
                    < 5.0,  # 5% threshold
                    "user_activity_tracked": len(compliance.get("unique_users", []))
                    > 0,
                },
            }

        except Exception as e:
            logger.error(f"Failed to get compliance report: {e}")
            return {"error": str(e)}

    async def search_audit_log(
        self,
        query: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user: Optional[str] = None,
        resource: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search audit log with advanced filtering"""
        try:
            audit_log = await cache.get(self.audit_log_key) or []

            # Apply time filters
            if start_time:
                audit_log = [
                    e
                    for e in audit_log
                    if datetime.fromisoformat(e["timestamp"]) >= start_time
                ]
            if end_time:
                audit_log = [
                    e
                    for e in audit_log
                    if datetime.fromisoformat(e["timestamp"]) <= end_time
                ]

            # Apply user filter
            if user:
                audit_log = [e for e in audit_log if e.get("user") == user]

            # Apply resource filter
            if resource:
                audit_log = [e for e in audit_log if e.get("resource") == resource]

            # Apply text search
            if query:
                query_lower = query.lower()
                audit_log = [
                    e
                    for e in audit_log
                    if (
                        query_lower in e.get("user", "").lower()
                        or query_lower in e.get("action", "").lower()
                        or query_lower in e.get("resource", "").lower()
                        or query_lower in e.get("error_message", "").lower()
                        if e.get("error_message")
                        else False
                    )
                ]

            # Sort by timestamp
            audit_log.sort(key=lambda x: x["timestamp"], reverse=True)

            return audit_log

        except Exception as e:
            logger.error(f"Failed to search audit log: {e}")
            return []

    async def export_audit_log(
        self,
        format: str = "json",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Union[str, Dict[str, Any]]:
        """Export audit log in various formats"""
        try:
            audit_log = await cache.get(self.audit_log_key) or []

            # Apply time filters
            if start_time:
                audit_log = [
                    e
                    for e in audit_log
                    if datetime.fromisoformat(e["timestamp"]) >= start_time
                ]
            if end_time:
                audit_log = [
                    e
                    for e in audit_log
                    if datetime.fromisoformat(e["timestamp"]) <= end_time
                ]

            if format.lower() == "json":
                return json.dumps(audit_log, indent=2)
            elif format.lower() == "csv":
                import csv
                import io

                output = io.StringIO()
                writer = csv.DictWriter(
                    output,
                    fieldnames=[
                        "event_id",
                        "timestamp",
                        "event_type",
                        "severity",
                        "user",
                        "action",
                        "resource",
                        "success",
                        "client_ip",
                        "user_agent",
                        "environment",
                        "session_id",
                        "request_id",
                        "response_time_ms",
                        "error_message",
                    ],
                )
                writer.writeheader()
                writer.writerows(audit_log)
                return output.getvalue()
            else:
                return {"error": f"Unsupported format: {format}"}

        except Exception as e:
            logger.error(f"Failed to export audit log: {e}")
            return {"error": str(e)}

    async def get_user_activity_report(
        self, user: str, days: int = 30
    ) -> Dict[str, Any]:
        """Get detailed activity report for a specific user"""
        try:
            audit_log = await cache.get(self.audit_log_key) or []

            # Filter by user and time range
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            user_events = [
                e
                for e in audit_log
                if e.get("user") == user
                and datetime.fromisoformat(e["timestamp"]) >= cutoff_time
            ]

            if not user_events:
                return {"user": user, "error": "No activity found for this user"}

            # Calculate metrics
            total_events = len(user_events)
            successful_events = len([e for e in user_events if e.get("success")])
            failed_events = total_events - successful_events

            # Group by action type
            actions = defaultdict(int)
            resources = defaultdict(int)
            severities = defaultdict(int)

            for event in user_events:
                actions[event.get("action", "unknown")] += 1
                resources[event.get("resource", "unknown")] += 1
                severities[event.get("severity", "unknown")] += 1

            # Calculate time distribution
            hours_distribution = defaultdict(int)
            for event in user_events:
                hour = datetime.fromisoformat(event["timestamp"]).hour
                hours_distribution[hour] += 1

            return {
                "user": user,
                "time_range": f"Last {days} days",
                "summary": {
                    "total_events": total_events,
                    "successful_events": successful_events,
                    "failed_events": failed_events,
                    "success_rate": round((successful_events / total_events * 100), 2)
                    if total_events > 0
                    else 0,
                },
                "activity_breakdown": {
                    "by_action": dict(actions),
                    "by_resource": dict(resources),
                    "by_severity": dict(severities),
                    "by_hour": dict(hours_distribution),
                },
                "last_activity": user_events[0]["timestamp"] if user_events else None,
            }

        except Exception as e:
            logger.error(f"Failed to get user activity report: {e}")
            return {"user": user, "error": str(e)}


# Global audit logger instance
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
    details: Dict[str, Any] = None,
    session_id: str = None,
    request_id: str = None,
    response_time_ms: float = None,
    error_message: str = None,
) -> str:
    """Convenience function to log ops events"""
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


async def get_audit_summary() -> Dict[str, Any]:
    """Get quick audit summary for dashboard"""
    try:
        compliance = await cache.get(audit_logger.compliance_key) or {}

        total_events = compliance.get("total_events", 0)
        failed_operations = compliance.get("failed_operations", 0)
        unique_users = len(compliance.get("unique_users", []))

        # Get recent activity
        audit_log = await cache.get(audit_logger.audit_log_key) or []
        recent_events = [
            e
            for e in audit_log
            if datetime.fromisoformat(e["timestamp"])
            >= datetime.utcnow() - timedelta(hours=1)
        ]

        # Get security alerts
        alerts = await cache.get(audit_logger.alerts_key) or []
        critical_alerts = [
            a
            for a in alerts
            if a.get("type") in ["critical_operation", "failed_authentication"]
        ]

        return {
            "total_events": total_events,
            "unique_users": unique_users,
            "failure_rate": round((failed_operations / total_events * 100), 2)
            if total_events > 0
            else 0,
            "recent_activity": len(recent_events),
            "security_alerts": len(critical_alerts),
            "last_updated": compliance.get("last_updated", "N/A"),
        }

    except Exception as e:
        logger.error(f"Failed to get audit summary: {e}")
        return {"error": str(e)}
