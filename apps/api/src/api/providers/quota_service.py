"""Provider/model quota coordination with Redis-backed reservations.

Public API is unchanged — callers import ``quota_service`` and ``QuotaReservation``
from this module.  Storage details live in ``quota_pkg/``.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, Optional

from .pricing import resolve_canonical_model, resolve_model_budget, resolve_rate_limit
from .quota_pkg.backend import QuotaBackend
from .quota_pkg.estimation import estimate_text_tokens
from .quota_pkg.memory_backend import MemoryQuotaBackend
from .quota_pkg.models import (
    _COOLDOWN_SECONDS,
    QuotaReservation,
    model_scope,
    provider_scope,
    window_key,
)
from .quota_pkg.redis_backend import RedisQuotaBackend

# Re-export so ``from .quota_service import QuotaReservation`` keeps working.
__all__ = ["ProviderQuotaService", "QuotaReservation", "quota_service"]


class ProviderQuotaService:
    def __init__(self) -> None:
        self._redis_backend = RedisQuotaBackend()
        self._memory_backend = MemoryQuotaBackend()
        self._last_skip_reason = ""
        self._pytest_current_test = os.getenv("PYTEST_CURRENT_TEST")

    def reset(self) -> None:
        self._redis_backend.reset()
        self._memory_backend.reset()
        self._last_skip_reason = ""
        self._pytest_current_test = os.getenv("PYTEST_CURRENT_TEST")

    @property
    def last_skip_reason(self) -> str:
        return self._last_skip_reason

    def _sync_test_context(self) -> None:
        current_test = os.getenv("PYTEST_CURRENT_TEST")
        if not current_test:
            return
        if current_test == self._pytest_current_test:
            return
        self._redis_backend.reset()
        self._memory_backend.reset()
        self._pytest_current_test = current_test

    async def _get_backend(self) -> QuotaBackend:
        rc = await self._redis_backend.get_redis_client()
        return self._redis_backend if rc is not None else self._memory_backend

    # ------------------------------------------------------------------
    # Token estimation (kept here so tests can monkeypatch resolve_model_budget)
    # ------------------------------------------------------------------

    def _estimate_tokens(
        self,
        *,
        messages: Optional[list[dict[str, Any]]] = None,
        prompt: str = "",
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> tuple[int, int]:
        input_tokens = estimate_text_tokens(prompt)
        if messages:
            input_tokens += sum(
                estimate_text_tokens(str(msg.get("content", ""))) for msg in messages
            )

        estimated_output = max(64, int(input_tokens * 0.5))
        if max_tokens is not None and max_tokens > 0:
            estimated_output = min(estimated_output, max_tokens)

        if model:
            provider_budget = resolve_model_budget(model)
            if provider_budget.tokens_per_minute > 0:
                estimated_output = min(estimated_output, provider_budget.tokens_per_minute)

        return max(0, input_tokens), max(0, estimated_output)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def reserve(
        self,
        provider_id: str,
        model: Optional[str],
        *,
        messages: Optional[list[dict[str, Any]]] = None,
        prompt: str = "",
        max_tokens: Optional[int] = None,
    ) -> Optional[QuotaReservation]:
        self._sync_test_context()
        self._last_skip_reason = ""

        if not await self.can_attempt(provider_id, model):
            self._last_skip_reason = "cooldown"
            return None

        canonical_model = resolve_canonical_model(model) or (model or "")
        provider_model = model or canonical_model or ""
        pscope = provider_scope(provider_id, provider_model)
        mscope = model_scope(canonical_model or provider_model)
        estimated_input, estimated_output = self._estimate_tokens(
            messages=messages,
            prompt=prompt,
            model=canonical_model or model,
            max_tokens=max_tokens,
        )

        provider_limit = resolve_rate_limit(provider_id, provider_model)
        shared_limit = resolve_model_budget(canonical_model or model)

        reservation = QuotaReservation(
            reservation_id=str(uuid.uuid4()),
            provider_id=provider_id,
            model=provider_model,
            canonical_model=canonical_model or provider_model,
            window_key=window_key(),
            estimated_input_tokens=estimated_input,
            estimated_output_tokens=estimated_output,
            provider_scope=pscope,
            model_scope=mscope,
            created_at=time.time(),
        )

        backend = await self._get_backend()
        ok = await backend.reserve(reservation, provider_limit, shared_limit)
        self._last_skip_reason = backend.last_skip_reason
        if not ok and not self._last_skip_reason:
            self._last_skip_reason = "capacity"
        return reservation if ok else None

    async def commit(
        self,
        reservation: QuotaReservation,
        *,
        actual_input_tokens: int = 0,
        actual_output_tokens: int = 0,
    ) -> None:
        self._sync_test_context()
        backend = await self._get_backend()
        await backend.commit(
            reservation,
            actual_input_tokens=actual_input_tokens,
            actual_output_tokens=actual_output_tokens,
        )

    async def release(self, reservation: QuotaReservation) -> None:
        self._sync_test_context()
        backend = await self._get_backend()
        await backend.release(reservation)

    async def mark_rate_limited(
        self,
        provider_id: str,
        model: Optional[str],
        *,
        cooldown_seconds: int = _COOLDOWN_SECONDS,
    ) -> None:
        self._sync_test_context()
        canonical_model = resolve_canonical_model(model) or (model or "")
        scopes = [
            provider_scope(provider_id, model or ""),
            model_scope(canonical_model or model or ""),
        ]
        backend = await self._get_backend()
        await backend.mark_rate_limited(scopes, cooldown_seconds)

    async def can_attempt(self, provider_id: str, model: Optional[str]) -> bool:
        self._sync_test_context()
        canonical_model = resolve_canonical_model(model) or (model or "")
        pscope = provider_scope(provider_id, model or canonical_model or "")
        mscope = model_scope(canonical_model or model or "")
        backend = await self._get_backend()
        return await backend.can_attempt(pscope, mscope)

    async def snapshot_provider(
        self,
        provider_id: str,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._sync_test_context()
        canonical_model = resolve_canonical_model(model) or (model or "")
        provider_model = model or canonical_model or ""
        wkey = window_key()
        pscope = provider_scope(provider_id, provider_model)
        mscope = model_scope(canonical_model or provider_model)
        backend = await self._get_backend()

        provider_snapshot = await backend.scope_snapshot(
            pscope, resolve_rate_limit(provider_id, provider_model), wkey
        )
        model_snapshot = await backend.scope_snapshot(
            mscope, resolve_model_budget(canonical_model or provider_model), wkey
        )

        return {
            "provider_id": provider_id,
            "model": provider_model or None,
            "canonical_model": canonical_model or None,
            "window_key": wkey,
            "provider_scope": provider_snapshot,
            "model_scope": model_snapshot,
        }


quota_service = ProviderQuotaService()
