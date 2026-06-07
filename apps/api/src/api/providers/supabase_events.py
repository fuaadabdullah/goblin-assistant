"""
Fire-and-forget Supabase writes for provider telemetry.

Two entry points used by the health monitor and dispatcher:
  upsert_provider_status(provider, is_healthy, circuit_state, ...)
  insert_routing_audit(request_id, model, ...)

All writes are best-effort: a network error is logged and swallowed so
caller code is never blocked or interrupted by telemetry.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
_ENABLED = bool(_SUPABASE_URL and _SERVICE_KEY)

_REST = f"{_SUPABASE_URL}/rest/v1" if _SUPABASE_URL else ""
_HEADERS = {
    "apikey": _SERVICE_KEY,
    "Authorization": f"Bearer {_SERVICE_KEY}",
    "Content-Type": "application/json",
}

# Shared client — created lazily, never closed (lives for process lifetime)
_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=5.0)
    return _client


async def _post(table: str, payload: Dict[str, Any], prefer: str) -> None:
    if not _ENABLED:
        return
    try:
        await _get_client().post(
            f"{_REST}/{table}",
            headers={**_HEADERS, "Prefer": prefer},
            json=payload,
        )
    except Exception as exc:
        logger.debug("supabase_event_write_failed table=%s error=%s", table, exc)


def _fire(coro: Any) -> None:
    """Schedule coro on the running loop without awaiting."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        pass


def upsert_provider_status(
    provider: str,
    *,
    is_healthy: bool,
    circuit_state: str,
    failure_count: int,
    transient_failure_count: Optional[int] = None,
    circuit_open_until: Optional[float] = None,
    avg_latency_ms: Optional[float] = None,
    error_message: Optional[str] = None,
) -> None:
    """Non-blocking upsert of a single provider's current health row."""
    payload: Dict[str, Any] = {
        "provider": provider,
        "is_healthy": is_healthy,
        "circuit_state": circuit_state,
        "failure_count": failure_count,
        "checked_at": "now()",
    }
    if transient_failure_count is not None:
        payload["transient_failure_count"] = transient_failure_count
    meaningful_until = circuit_open_until is not None and circuit_open_until not in (
        0.0,
        float("inf"),
    )
    payload["circuit_open_until"] = circuit_open_until if meaningful_until else None
    if avg_latency_ms is not None:
        payload["avg_latency_ms"] = round(avg_latency_ms, 2)
    if error_message is not None:
        payload["error_message"] = error_message[:500]

    _fire(
        _post(
            "provider_status",
            payload,
            "resolution=merge-duplicates,return=minimal",
        )
    )


def insert_routing_audit(
    request_id: str,
    model: str,
    *,
    user_id: Optional[str] = None,
    routing_mode: Optional[str] = None,
    selected_provider: Optional[str] = None,
    attempted_providers: Optional[List[str]] = None,
    latency_ms: Optional[int] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    cost_usd: Optional[float] = None,
    success: bool,
    error_message: Optional[str] = None,
    error_category: Optional[str] = None,
) -> None:
    """Non-blocking insert of one routing decision into the audit log."""
    payload: Dict[str, Any] = {
        "request_id": request_id,
        "model": model,
        "success": success,
    }
    if user_id:
        payload["user_id"] = user_id
    if routing_mode:
        payload["routing_mode"] = routing_mode
    if selected_provider:
        payload["selected_provider"] = selected_provider
    if attempted_providers:
        payload["attempted_providers"] = attempted_providers
    if latency_ms is not None:
        payload["latency_ms"] = latency_ms
    if input_tokens is not None:
        payload["input_tokens"] = input_tokens
    if output_tokens is not None:
        payload["output_tokens"] = output_tokens
    if cost_usd is not None:
        payload["cost_usd"] = round(cost_usd, 8)
    if error_message:
        payload["error_message"] = error_message[:500]
    if error_category:
        payload["error_category"] = error_category

    _fire(_post("routing_audit_log", payload, "return=minimal"))


async def check_provider_access(user_id: str, provider_id: str) -> bool:
    """Check if user has access to a provider.

    Returns True (allow) by default when:
    - Supabase is not configured
    - No row exists for (user_id, provider_id) — default-open policy
    - Network/parse error — fail open to avoid blocking legitimate requests

    Returns False only when an explicit deny row exists.
    """
    if not _ENABLED:
        return True
    try:
        resp = await _get_client().get(
            f"{_REST}/user_provider_access",
            headers=_HEADERS,
            params={
                "user_id": f"eq.{user_id}",
                "provider_id": f"eq.{provider_id}",
                "select": "allowed",
                "limit": "1",
            },
        )
        rows = resp.json()
        if rows:
            return bool(rows[0]["allowed"])
        return True
    except Exception as exc:
        logger.debug(
            "supabase_access_check_failed user_id=%s provider=%s error=%s",
            user_id,
            provider_id,
            exc,
        )
        return True
