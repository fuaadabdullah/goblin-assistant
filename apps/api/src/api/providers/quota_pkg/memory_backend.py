"""In-memory quota backend — used when Redis is unavailable or in tests."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List

from .backend import QuotaBackend
from .models import (
    _RESERVATION_TTL_SECONDS,
    QuotaReservation,
    format_snapshot,
    memory_scope_key,
    reservation_key,
)


class MemoryQuotaBackend(QuotaBackend):
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._store: Dict[str, Any] = {}
        self._last_skip_reason = ""

    @property
    def last_skip_reason(self) -> str:
        return self._last_skip_reason

    def reset(self) -> None:
        self._store.clear()
        self._last_skip_reason = ""

    async def reserve(
        self,
        reservation: QuotaReservation,
        provider_limit: Any,
        shared_limit: Any,
    ) -> bool:
        self._last_skip_reason = ""
        async with self._lock:
            pscope = memory_scope_key(reservation.provider_scope, reservation.window_key)
            mscope = memory_scope_key(reservation.model_scope, reservation.window_key)
            if not self._has_capacity(pscope, provider_limit, reservation):
                self._last_skip_reason = "provider-capacity"
                return False
            if not self._has_capacity(mscope, shared_limit, reservation):
                self._last_skip_reason = "model-capacity"
                return False
            self._increment(pscope, reservation)
            self._increment(mscope, reservation)
            self._store[reservation_key(reservation.reservation_id)] = {
                "reservation": reservation,
                "expires_at": time.time() + _RESERVATION_TTL_SECONDS,
            }
        return True

    async def commit(
        self,
        reservation: QuotaReservation,
        *,
        actual_input_tokens: int = 0,
        actual_output_tokens: int = 0,
    ) -> None:
        actual_total = max(0, actual_input_tokens + actual_output_tokens)
        async with self._lock:
            self._finalize(reservation, actual_total, committed=True)

    async def release(self, reservation: QuotaReservation) -> None:
        async with self._lock:
            self._finalize(reservation, 0, committed=False)

    async def mark_rate_limited(self, scopes: List[str], cooldown_seconds: int) -> None:
        async with self._lock:
            now = time.time()
            for scope in scopes:
                self._store.setdefault(scope, {})["cooldown_until"] = now + max(1, cooldown_seconds)

    async def can_attempt(self, provider_scope: str, model_scope: str) -> bool:
        async with self._lock:
            now = time.time()
            ps = self._store.get(provider_scope, {})
            ms = self._store.get(model_scope, {})
            return now >= float(ps.get("cooldown_until", 0.0)) and now >= float(
                ms.get("cooldown_until", 0.0)
            )

    async def scope_snapshot(self, scope: str, limit: Any, wkey: str) -> Dict[str, Any]:
        async with self._lock:
            state = self._store.get(memory_scope_key(scope, wkey), {})
            reserved_requests = int(state.get("reserved_requests", 0))
            reserved_tokens = int(state.get("reserved_tokens", 0))
            committed_requests = int(state.get("committed_requests", 0))
            committed_tokens = int(state.get("committed_tokens", 0))
            active = int(state.get("active", 0))
            cooldown_remaining = max(
                0.0,
                float(self._store.get(scope, {}).get("cooldown_until", 0.0)) - time.time(),
            )
        return format_snapshot(
            scope,
            wkey,
            limit,
            reserved_requests,
            reserved_tokens,
            committed_requests,
            committed_tokens,
            active,
            cooldown_remaining,
        )

    # ------------------------------------------------------------------
    # Private helpers (called under self._lock)
    # ------------------------------------------------------------------

    def _has_capacity(
        self,
        scope: str,
        limit: Any,
        reservation: QuotaReservation,
    ) -> bool:
        if not limit or (
            int(getattr(limit, "requests_per_minute", 0) or 0) <= 0
            and int(getattr(limit, "tokens_per_minute", 0) or 0) <= 0
            and int(getattr(limit, "concurrency", 0) or 0) <= 0
        ):
            return True
        state = self._store.setdefault(scope, {})
        projected_requests = (
            int(state.get("committed_requests", 0)) + int(state.get("reserved_requests", 0)) + 1
        )
        projected_tokens = (
            int(state.get("committed_tokens", 0))
            + int(state.get("reserved_tokens", 0))
            + reservation.estimated_total_tokens
        )
        active = int(state.get("active", 0))
        rpm = int(getattr(limit, "requests_per_minute", 0) or 0)
        tpm = int(getattr(limit, "tokens_per_minute", 0) or 0)
        concurrency = int(getattr(limit, "concurrency", 0) or 0)
        if rpm > 0 and projected_requests > rpm:
            return False
        if tpm > 0 and projected_tokens > tpm:
            return False
        if concurrency > 0 and active + 1 > concurrency:
            return False
        return True

    def _increment(self, scope: str, reservation: QuotaReservation) -> None:
        state = self._store.setdefault(scope, {})
        state["reserved_requests"] = int(state.get("reserved_requests", 0)) + 1
        state["reserved_tokens"] = (
            int(state.get("reserved_tokens", 0)) + reservation.estimated_total_tokens
        )
        state["active"] = int(state.get("active", 0)) + 1

    def _finalize(
        self,
        reservation: QuotaReservation,
        actual_total: int,
        *,
        committed: bool,
    ) -> None:
        pscope = memory_scope_key(reservation.provider_scope, reservation.window_key)
        mscope = memory_scope_key(reservation.model_scope, reservation.window_key)
        if committed:
            self._decrement_reserved_and_commit(
                pscope, reservation.estimated_total_tokens, actual_total
            )
            self._decrement_reserved_and_commit(
                mscope, reservation.estimated_total_tokens, actual_total
            )
        else:
            self._decrement_reserved(pscope, reservation.estimated_total_tokens)
            self._decrement_reserved(mscope, reservation.estimated_total_tokens)
        self._store.pop(reservation_key(reservation.reservation_id), None)

    def _decrement_reserved_and_commit(
        self, scope: str, reserved_total: int, actual_total: int
    ) -> None:
        state = self._store.setdefault(scope, {})
        state["reserved_requests"] = max(0, int(state.get("reserved_requests", 0)) - 1)
        state["reserved_tokens"] = max(0, int(state.get("reserved_tokens", 0)) - reserved_total)
        state["active"] = max(0, int(state.get("active", 0)) - 1)
        state["committed_requests"] = int(state.get("committed_requests", 0)) + 1
        state["committed_tokens"] = int(state.get("committed_tokens", 0)) + actual_total

    def _decrement_reserved(self, scope: str, reserved_total: int) -> None:
        state = self._store.setdefault(scope, {})
        state["reserved_requests"] = max(0, int(state.get("reserved_requests", 0)) - 1)
        state["reserved_tokens"] = max(0, int(state.get("reserved_tokens", 0)) - reserved_total)
        state["active"] = max(0, int(state.get("active", 0)) - 1)
