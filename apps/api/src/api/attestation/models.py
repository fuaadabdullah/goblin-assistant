"""Shared models and constants for attestation."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Dict, Optional

# Input validation patterns
NODE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")

# Boolean serialization sentinel values
VERIFIED_TRUE = "1"
VERIFIED_FALSE = "0"


@dataclass
class CachedAttestation:
    """Type-safe wrapper for cached attestation results from Redis."""

    node_id: str
    verified: str
    provider: str
    timestamp: str
    cache_until: str
    grace_period_until: str
    violations: Optional[str] = None
    error: Optional[str] = None
    measured_at: Optional[str] = None
    enclave_id: Optional[str] = None
    shielded_vm_enabled: Optional[str] = None
    integrity_monitoring_enabled: Optional[str] = None
    instance_id: Optional[str] = None

    @classmethod
    def from_redis_dict(cls, data: Dict[str, str]) -> "CachedAttestation":
        return cls(
            node_id=data.get("node_id", ""),
            verified=data.get("verified", VERIFIED_FALSE),
            provider=data.get("provider", ""),
            timestamp=data.get("timestamp", ""),
            cache_until=data.get("cache_until", ""),
            grace_period_until=data.get("grace_period_until", ""),
            violations=data.get("violations"),
            error=data.get("error"),
            measured_at=data.get("measured_at"),
            enclave_id=data.get("enclave_id"),
            shielded_vm_enabled=data.get("shielded_vm_enabled"),
            integrity_monitoring_enabled=data.get("integrity_monitoring_enabled"),
            instance_id=data.get("instance_id"),
        )

    def to_redis_dict(self) -> Dict[str, str]:
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                result[key] = str(value)
        return result
