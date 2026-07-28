"""Shared data model, constants, and key-generation helpers for the quota system."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_WINDOW_SECONDS = 60
_RESERVATION_TTL_SECONDS = 180
_COOLDOWN_SECONDS = 30


@dataclass(frozen=True)
class QuotaReservation:
    reservation_id: str
    provider_id: str
    model: str
    canonical_model: str
    window_key: str
    estimated_input_tokens: int
    estimated_output_tokens: int
    provider_scope: str
    model_scope: str
    created_at: float

    @property
    def estimated_total_tokens(self) -> int:
        return max(0, self.estimated_input_tokens + self.estimated_output_tokens)


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------


def window_key(moment: Optional[datetime] = None) -> str:
    now = moment or datetime.now(timezone.utc)
    return now.strftime("%Y%m%d%H%M")


def provider_scope(provider_id: str, model: str) -> str:
    return f"provider:{provider_id}:model:{model}"


def model_scope(canonical_model: str) -> str:
    return f"model:{canonical_model}"


def reservation_key(reservation_id: str) -> str:
    return f"quota:reservation:{reservation_id}"


def cooldown_key(scope: str) -> str:
    return f"quota:cooldown:{scope}"


def scope_keys(scope: str, wkey: str) -> Dict[str, str]:
    prefix = f"quota:{scope}:{wkey}"
    return {
        "reserved_requests": f"{prefix}:reserved:requests",
        "reserved_tokens": f"{prefix}:reserved:tokens",
        "committed_requests": f"{prefix}:committed:requests",
        "committed_tokens": f"{prefix}:committed:tokens",
        "active": f"{prefix}:active",
    }


def memory_scope_key(scope: str, wkey: str) -> str:
    return f"{scope}:{wkey}"


# ---------------------------------------------------------------------------
# Static utilities
# ---------------------------------------------------------------------------


def normalized_limit(limit: Any) -> Dict[str, int]:
    if limit is None:
        return {"requests_per_minute": 0, "tokens_per_minute": 0, "concurrency": 0}
    return {
        "requests_per_minute": int(getattr(limit, "requests_per_minute", 0) or 0),
        "tokens_per_minute": int(getattr(limit, "tokens_per_minute", 0) or 0),
        "concurrency": int(getattr(limit, "concurrency", 0) or 0),
    }


def remaining_value(limit_value: int, used_value: int) -> Optional[int]:
    if limit_value <= 0:
        return None
    return max(0, limit_value - used_value)


def serialize_reservation(reservation: QuotaReservation) -> str:
    return "|".join(
        [
            reservation.reservation_id,
            reservation.provider_id,
            reservation.model,
            reservation.canonical_model,
            str(reservation.estimated_input_tokens),
            str(reservation.estimated_output_tokens),
        ]
    )


def limit_arg(limit: Any, name: str) -> int:
    return int(getattr(limit, name, 0) or 0)


def format_snapshot(
    scope: str,
    wkey: str,
    limit: Any,
    reserved_requests: int,
    reserved_tokens: int,
    committed_requests: int,
    committed_tokens: int,
    active: int,
    cooldown_remaining_seconds: float,
) -> Dict[str, Any]:
    nlimit = normalized_limit(limit)
    used_requests = committed_requests + reserved_requests
    used_tokens = committed_tokens + reserved_tokens
    return {
        "scope": scope,
        "window_key": wkey,
        "limits": nlimit,
        "usage": {
            "reserved_requests": reserved_requests,
            "reserved_tokens": reserved_tokens,
            "committed_requests": committed_requests,
            "committed_tokens": committed_tokens,
            "active": active,
        },
        "remaining_requests": remaining_value(nlimit["requests_per_minute"], used_requests),
        "remaining_tokens": remaining_value(nlimit["tokens_per_minute"], used_tokens),
        "remaining_concurrency": remaining_value(nlimit["concurrency"], active),
        "cooldown_remaining_seconds": round(max(0.0, cooldown_remaining_seconds), 1),
    }
