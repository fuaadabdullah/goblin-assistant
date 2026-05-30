"""Audit models and enums."""

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class AuditEventType(Enum):
    """Types of audit events."""

    READ = "read"
    WRITE = "write"
    RESET = "reset"
    DEBUG = "debug"
    SECURITY = "security"
    SYSTEM = "system"


class AuditSeverity(Enum):
    """Severity levels for audit events."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Structured audit event with all necessary metadata."""

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
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["event_type"] = self.event_type.value
        data["severity"] = self.severity.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvent":
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["event_type"] = AuditEventType(data["event_type"])
        data["severity"] = AuditSeverity(data["severity"])
        return cls(**data)
