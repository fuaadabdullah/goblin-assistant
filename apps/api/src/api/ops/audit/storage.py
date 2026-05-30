"""Audit storage and query helpers."""

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from ...storage.cache import cache
from .models import AuditEvent, AuditSeverity

logger = logging.getLogger(__name__)


class AuditStore:
    def __init__(self, audit_log_key: str, compliance_key: str, alerts_key: str):
        self.audit_log_key = audit_log_key
        self.compliance_key = compliance_key
        self.alerts_key = alerts_key

    async def store_event(self, event: AuditEvent) -> None:
        try:
            audit_log = await cache.get(self.audit_log_key) or []
            audit_log.append(event.to_dict())
            if len(audit_log) > 10000:
                audit_log = audit_log[-10000:]
            await cache.set(self.audit_log_key, audit_log, expire=86400 * 30)
        except Exception as e:
            logger.error(f"Failed to store audit event: {e}")

    async def update_compliance_metrics(self, event: AuditEvent) -> None:
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
            compliance["total_events"] += 1
            compliance["events_by_type"][event.event_type.value] += 1
            compliance["events_by_severity"][event.severity.value] += 1
            compliance["events_by_user"][event.user] += 1
            hour_key = event.timestamp.strftime("%Y-%m-%d %H")
            compliance["events_by_hour"][hour_key] += 1
            if not event.success:
                compliance["failed_operations"] += 1
            compliance["unique_users"].add(event.user)
            compliance["last_updated"] = datetime.utcnow().isoformat()
            compliance["unique_users"] = list(compliance["unique_users"])
            await cache.set(self.compliance_key, compliance, expire=86400 * 90)
        except Exception as e:
            logger.error(f"Failed to update compliance metrics: {e}")

    async def get_audit_log(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            audit_log = await cache.get(self.audit_log_key) or []
            if filters:
                filtered_log = []
                for event in audit_log:
                    if all(event.get(key) == value for key, value in filters.items()):
                        filtered_log.append(event)
                audit_log = filtered_log
            audit_log.sort(key=lambda x: x["timestamp"], reverse=True)
            return audit_log[offset : offset + limit]
        except Exception as e:
            logger.error(f"Failed to get audit log: {e}")
            return []

    async def get_security_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            alerts = await cache.get(self.alerts_key) or []
            return alerts[-limit:]
        except Exception as e:
            logger.error(f"Failed to get security alerts: {e}")
            return []

    async def get_compliance_report(self) -> Dict[str, Any]:
        try:
            compliance = await cache.get(self.compliance_key) or {}
            total_events = compliance.get("total_events", 0)
            failed_operations = compliance.get("failed_operations", 0)
            failure_rate = (failed_operations / total_events * 100) if total_events > 0 else 0
            events_by_hour = compliance.get("events_by_hour", {})
            peak_hour = max(events_by_hour.items(), key=lambda x: x[1], default=("N/A", 0))
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
                    "failed_operations_under_threshold": failure_rate < 5.0,
                    "user_activity_tracked": len(compliance.get("unique_users", [])) > 0,
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
        try:
            audit_log = await cache.get(self.audit_log_key) or []
            if start_time:
                audit_log = [
                    e for e in audit_log if datetime.fromisoformat(e["timestamp"]) >= start_time
                ]
            if end_time:
                audit_log = [
                    e for e in audit_log if datetime.fromisoformat(e["timestamp"]) <= end_time
                ]
            if user:
                audit_log = [e for e in audit_log if e.get("user") == user]
            if resource:
                audit_log = [e for e in audit_log if e.get("resource") == resource]
            if query:
                query_lower = query.lower()
                audit_log = [
                    e
                    for e in audit_log
                    if (
                        query_lower in e.get("user", "").lower()
                        or query_lower in e.get("action", "").lower()
                        or query_lower in e.get("resource", "").lower()
                        or (
                            query_lower in e.get("error_message", "").lower()
                            if e.get("error_message")
                            else False
                        )
                    )
                ]
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
        try:
            audit_log = await cache.get(self.audit_log_key) or []
            if start_time:
                audit_log = [
                    e for e in audit_log if datetime.fromisoformat(e["timestamp"]) >= start_time
                ]
            if end_time:
                audit_log = [
                    e for e in audit_log if datetime.fromisoformat(e["timestamp"]) <= end_time
                ]
            if format.lower() == "json":
                return json.dumps(audit_log, indent=2)
            if format.lower() == "csv":
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
            return {"error": f"Unsupported format: {format}"}
        except Exception as e:
            logger.error(f"Failed to export audit log: {e}")
            return {"error": str(e)}

    async def get_user_activity_report(self, user: str, days: int = 30) -> Dict[str, Any]:
        try:
            audit_log = await cache.get(self.audit_log_key) or []
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            user_events = [
                e
                for e in audit_log
                if e.get("user") == user and datetime.fromisoformat(e["timestamp"]) >= cutoff_time
            ]
            if not user_events:
                return {"user": user, "error": "No activity found for this user"}

            total_events = len(user_events)
            successful_events = len([e for e in user_events if e.get("success")])
            failed_events = total_events - successful_events
            actions = defaultdict(int)
            resources = defaultdict(int)
            severities = defaultdict(int)
            for event in user_events:
                actions[event.get("action", "unknown")] += 1
                resources[event.get("resource", "unknown")] += 1
                severities[event.get("severity", "unknown")] += 1
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
                    "success_rate": (
                        round((successful_events / total_events * 100), 2)
                        if total_events > 0
                        else 0
                    ),
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

    async def get_summary(self) -> Dict[str, Any]:
        try:
            compliance = await cache.get(self.compliance_key) or {}
            total_events = compliance.get("total_events", 0)
            failed_operations = compliance.get("failed_operations", 0)
            unique_users = len(compliance.get("unique_users", []))
            audit_log = await cache.get(self.audit_log_key) or []
            recent_events = [
                e
                for e in audit_log
                if datetime.fromisoformat(e["timestamp"]) >= datetime.utcnow() - timedelta(hours=1)
            ]
            alerts = await cache.get(self.alerts_key) or []
            critical_alerts = [
                a
                for a in alerts
                if a.get("type") in ["critical_operation", "failed_authentication"]
            ]
            return {
                "total_events": total_events,
                "unique_users": unique_users,
                "failure_rate": (
                    round((failed_operations / total_events * 100), 2) if total_events > 0 else 0
                ),
                "recent_activity": len(recent_events),
                "security_alerts": len(critical_alerts),
                "last_updated": compliance.get("last_updated", "N/A"),
            }
        except Exception as e:
            logger.error(f"Failed to get audit summary: {e}")
            return {"error": str(e)}

    async def check_security_alerts(self, event: AuditEvent) -> None:
        try:
            alerts = await cache.get(self.alerts_key) or []
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
            if alerts:
                await cache.set(self.alerts_key, alerts[-1000:], expire=86400 * 7)
        except Exception as e:
            logger.error(f"Failed to check security alerts: {e}")
