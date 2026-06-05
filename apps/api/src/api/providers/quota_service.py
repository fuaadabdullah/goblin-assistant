"""Provider/model quota coordination with Redis-backed reservations."""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis.asyncio as redis
import structlog

from api.services.retrieval_service._token_budget import estimate_tokens

from .pricing import resolve_canonical_model, resolve_model_budget, resolve_rate_limit

logger = structlog.get_logger(__name__)

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


class ProviderQuotaService:
    def __init__(self) -> None:
        self._memory_lock = asyncio.Lock()
        self._memory: Dict[str, Dict[str, Any]] = {}
        self._redis_client: Any = None
        self._redis_failed = False
        self._pytest_current_test = os.getenv("PYTEST_CURRENT_TEST")
        self._last_skip_reason = ""

    def reset(self) -> None:
        self._memory.clear()
        self._redis_client = None
        self._redis_failed = False
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
        self._memory.clear()
        self._redis_client = None
        self._redis_failed = False
        self._pytest_current_test = current_test

    def _window_key(self, moment: Optional[datetime] = None) -> str:
        now = moment or datetime.now(timezone.utc)
        return now.strftime("%Y%m%d%H%M")

    def _provider_scope(self, provider_id: str, model: str) -> str:
        return f"provider:{provider_id}:model:{model}"

    def _model_scope(self, canonical_model: str) -> str:
        return f"model:{canonical_model}"

    def _reservation_key(self, reservation_id: str) -> str:
        return f"quota:reservation:{reservation_id}"

    def _cooldown_key(self, scope: str) -> str:
        return f"quota:cooldown:{scope}"

    def _scope_keys(self, scope: str, window_key: str) -> Dict[str, str]:
        prefix = f"quota:{scope}:{window_key}"
        return {
            "reserved_requests": f"{prefix}:reserved:requests",
            "reserved_tokens": f"{prefix}:reserved:tokens",
            "committed_requests": f"{prefix}:committed:requests",
            "committed_tokens": f"{prefix}:committed:tokens",
            "active": f"{prefix}:active",
        }

    def _memory_scope_key(self, scope: str, window_key: str) -> str:
        return f"{scope}:{window_key}"

    async def _get_redis(self):
        if self._redis_failed:
            return None
        if os.getenv("PYTEST_CURRENT_TEST"):
            return None
        if os.getenv("PROVIDER_QUOTA_USE_REDIS", "").strip().lower() not in {
            "1",
            "true",
            "yes",
            "on",
        }:
            return None
        if self._redis_client is not None:
            return self._redis_client
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self._redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                retry_on_timeout=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            await self._redis_client.ping()
            return self._redis_client
        except Exception as exc:  # noqa: BLE001
            self._redis_failed = True
            logger.debug("quota_redis_unavailable", error=str(exc))
            return None

    def _estimate_tokens(
        self,
        *,
        messages: Optional[list[dict[str, Any]]] = None,
        prompt: str = "",
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> tuple[int, int]:
        input_tokens = estimate_tokens(prompt)
        if messages:
            input_tokens += sum(estimate_tokens(str(msg.get("content", ""))) for msg in messages)

        # Keep the estimate conservative but not overly punitive.
        estimated_output = max(64, int(input_tokens * 0.5))
        if max_tokens is not None and max_tokens > 0:
            estimated_output = min(estimated_output, max_tokens)

        if model:
            provider_budget = resolve_model_budget(model)
            if provider_budget.tokens_per_minute > 0:
                estimated_output = min(estimated_output, provider_budget.tokens_per_minute)

        return max(0, input_tokens), max(0, estimated_output)

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
        provider_scope = self._provider_scope(provider_id, provider_model)
        model_scope = self._model_scope(canonical_model or provider_model)
        estimated_input_tokens, estimated_output_tokens = self._estimate_tokens(
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
            window_key=self._window_key(),
            estimated_input_tokens=estimated_input_tokens,
            estimated_output_tokens=estimated_output_tokens,
            provider_scope=provider_scope,
            model_scope=model_scope,
            created_at=time.time(),
        )

        redis_client = await self._get_redis()
        if redis_client is not None:
            ok = await self._reserve_with_redis(
                redis_client,
                reservation,
                provider_limit,
                shared_limit,
            )
        else:
            ok = await self._reserve_in_memory(reservation, provider_limit, shared_limit)

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
        redis_client = await self._get_redis()
        if redis_client is not None:
            await self._commit_with_redis(
                redis_client,
                reservation,
                actual_input_tokens=actual_input_tokens,
                actual_output_tokens=actual_output_tokens,
            )
            return
        await self._commit_in_memory(
            reservation,
            actual_input_tokens=actual_input_tokens,
            actual_output_tokens=actual_output_tokens,
        )

    async def release(self, reservation: QuotaReservation) -> None:
        self._sync_test_context()
        redis_client = await self._get_redis()
        if redis_client is not None:
            await self._release_with_redis(redis_client, reservation)
            return
        await self._release_in_memory(reservation)

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
            self._provider_scope(provider_id, model or ""),
            self._model_scope(canonical_model or model or ""),
        ]
        redis_client = await self._get_redis()
        if redis_client is not None:
            for scope in scopes:
                await redis_client.set(
                    self._cooldown_key(scope),
                    "1",
                    ex=max(1, cooldown_seconds),
                )
            return

        async with self._memory_lock:
            now = time.time()
            for scope in scopes:
                self._memory.setdefault(scope, {})["cooldown_until"] = now + max(1, cooldown_seconds)

    async def can_attempt(self, provider_id: str, model: Optional[str]) -> bool:
        self._sync_test_context()
        canonical_model = resolve_canonical_model(model) or (model or "")
        provider_scope = self._provider_scope(provider_id, model or canonical_model or "")
        model_scope = self._model_scope(canonical_model or model or "")
        redis_client = await self._get_redis()
        if redis_client is not None:
            return not (
                await redis_client.exists(self._cooldown_key(provider_scope))
                or await redis_client.exists(self._cooldown_key(model_scope))
            )
        async with self._memory_lock:
            now = time.time()
            provider_state = self._memory.get(provider_scope, {})
            model_state = self._memory.get(model_scope, {})
            return now >= float(provider_state.get("cooldown_until", 0.0)) and now >= float(
                model_state.get("cooldown_until", 0.0)
            )

    async def _reserve_with_redis(
        self,
        redis_client: Any,
        reservation: QuotaReservation,
        provider_limit: Any,
        shared_limit: Any,
    ) -> bool:
        if await redis_client.exists(self._cooldown_key(reservation.provider_scope)):
            self._last_skip_reason = "provider-cooldown"
            return False
        if await redis_client.exists(self._cooldown_key(reservation.model_scope)):
            self._last_skip_reason = "model-cooldown"
            return False

        now = datetime.now(timezone.utc)
        window_key = self._window_key(now)
        keys = {
            "provider": self._scope_keys(reservation.provider_scope, window_key),
            "model": self._scope_keys(reservation.model_scope, window_key),
        }

        ok = int(
            await redis_client.eval(
                self._reserve_lua(),
                11,
                keys["provider"]["reserved_requests"],
                keys["provider"]["reserved_tokens"],
                keys["provider"]["committed_requests"],
                keys["provider"]["committed_tokens"],
                keys["provider"]["active"],
                keys["model"]["reserved_requests"],
                keys["model"]["reserved_tokens"],
                keys["model"]["committed_requests"],
                keys["model"]["committed_tokens"],
                keys["model"]["active"],
                self._reservation_key(reservation.reservation_id),
                self._limit_arg(provider_limit, "requests_per_minute"),
                self._limit_arg(provider_limit, "tokens_per_minute"),
                self._limit_arg(provider_limit, "concurrency"),
                self._limit_arg(shared_limit, "requests_per_minute"),
                self._limit_arg(shared_limit, "tokens_per_minute"),
                self._limit_arg(shared_limit, "concurrency"),
                reservation.estimated_total_tokens,
                _WINDOW_SECONDS * 2,
                self._serialize_reservation(reservation),
                _RESERVATION_TTL_SECONDS,
            )
            or 0
        )
        if ok == 1:
            return True
        self._last_skip_reason = {
            2: "provider-requests",
            3: "provider-tokens",
            4: "provider-concurrency",
            5: "model-requests",
            6: "model-tokens",
            7: "model-concurrency",
        }.get(ok, "capacity")
        return False

    async def _reserve_in_memory(
        self,
        reservation: QuotaReservation,
        provider_limit: Any,
        shared_limit: Any,
    ) -> bool:
        async with self._memory_lock:
            provider_scope = self._memory_scope_key(
                reservation.provider_scope,
                reservation.window_key,
            )
            model_scope = self._memory_scope_key(
                reservation.model_scope,
                reservation.window_key,
            )
            if not self._has_capacity_in_memory(provider_scope, provider_limit, reservation):
                self._last_skip_reason = "provider-capacity"
                return False
            if not self._has_capacity_in_memory(model_scope, shared_limit, reservation):
                self._last_skip_reason = "model-capacity"
                return False
            self._increment_in_memory(provider_scope, reservation)
            self._increment_in_memory(model_scope, reservation)
            self._memory[self._reservation_key(reservation.reservation_id)] = {
                "reservation": reservation,
                "expires_at": time.time() + _RESERVATION_TTL_SECONDS,
            }
        return True

    async def _commit_with_redis(
        self,
        redis_client: Any,
        reservation: QuotaReservation,
        *,
        actual_input_tokens: int = 0,
        actual_output_tokens: int = 0,
    ) -> None:
        actual_total = max(0, actual_input_tokens + actual_output_tokens)
        await self._finalize_with_redis(redis_client, reservation, actual_total, committed=True)

    async def _release_with_redis(self, redis_client: Any, reservation: QuotaReservation) -> None:
        await self._finalize_with_redis(redis_client, reservation, 0, committed=False)

    async def _finalize_with_redis(
        self,
        redis_client: Any,
        reservation: QuotaReservation,
        actual_total: int,
        *,
        committed: bool,
    ) -> None:
        window_key = reservation.window_key
        provider_keys = self._scope_keys(reservation.provider_scope, window_key)
        model_keys = self._scope_keys(reservation.model_scope, window_key)
        if committed:
            await self._decrement_reserved_and_increment_committed(
                redis_client,
                provider_keys,
                reservation.estimated_total_tokens,
                actual_total,
            )
            await self._decrement_reserved_and_increment_committed(
                redis_client,
                model_keys,
                reservation.estimated_total_tokens,
                actual_total,
            )
        else:
            await self._decrement_reserved(redis_client, provider_keys, reservation.estimated_total_tokens)
            await self._decrement_reserved(redis_client, model_keys, reservation.estimated_total_tokens)
        await redis_client.delete(self._reservation_key(reservation.reservation_id))

    async def _commit_in_memory(
        self,
        reservation: QuotaReservation,
        *,
        actual_input_tokens: int = 0,
        actual_output_tokens: int = 0,
    ) -> None:
        actual_total = max(0, actual_input_tokens + actual_output_tokens)
        async with self._memory_lock:
            self._finalize_in_memory(reservation, actual_total, committed=True)

    async def _release_in_memory(self, reservation: QuotaReservation) -> None:
        async with self._memory_lock:
            self._finalize_in_memory(reservation, 0, committed=False)

    def _finalize_in_memory(
        self,
        reservation: QuotaReservation,
        actual_total: int,
        *,
        committed: bool,
    ) -> None:
        provider_scope = self._memory_scope_key(reservation.provider_scope, reservation.window_key)
        model_scope = self._memory_scope_key(reservation.model_scope, reservation.window_key)
        if committed:
            self._decrement_reserved_and_increment_committed_in_memory(
                provider_scope,
                reservation.estimated_total_tokens,
                actual_total,
            )
            self._decrement_reserved_and_increment_committed_in_memory(
                model_scope,
                reservation.estimated_total_tokens,
                actual_total,
            )
        else:
            self._decrement_reserved_in_memory(provider_scope, reservation.estimated_total_tokens)
            self._decrement_reserved_in_memory(model_scope, reservation.estimated_total_tokens)
        self._memory.pop(self._reservation_key(reservation.reservation_id), None)

    async def _has_capacity(
        self,
        redis_client: Any,
        scope_keys: Dict[str, str],
        limit: Any,
        reservation: QuotaReservation,
    ) -> bool:
        if not limit or (
            int(getattr(limit, "requests_per_minute", 0) or 0) <= 0
            and int(getattr(limit, "tokens_per_minute", 0) or 0) <= 0
            and int(getattr(limit, "concurrency", 0) or 0) <= 0
        ):
            return True

        reserved_requests = int(await redis_client.get(scope_keys["reserved_requests"]) or 0)
        reserved_tokens = int(await redis_client.get(scope_keys["reserved_tokens"]) or 0)
        committed_requests = int(await redis_client.get(scope_keys["committed_requests"]) or 0)
        committed_tokens = int(await redis_client.get(scope_keys["committed_tokens"]) or 0)
        active = int(await redis_client.get(scope_keys["active"]) or 0)

        projected_requests = committed_requests + reserved_requests + 1
        projected_tokens = committed_tokens + reserved_tokens + reservation.estimated_total_tokens

        requests_limit = int(getattr(limit, "requests_per_minute", 0) or 0)
        tokens_limit = int(getattr(limit, "tokens_per_minute", 0) or 0)
        concurrency_limit = int(getattr(limit, "concurrency", 0) or 0)

        if requests_limit > 0 and projected_requests > requests_limit:
            return False
        if tokens_limit > 0 and projected_tokens > tokens_limit:
            return False
        if concurrency_limit > 0 and active + 1 > concurrency_limit:
            return False
        return True

    def _has_capacity_in_memory(
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

        state = self._memory.setdefault(scope, {})
        reserved_requests = int(state.get("reserved_requests", 0))
        reserved_tokens = int(state.get("reserved_tokens", 0))
        committed_requests = int(state.get("committed_requests", 0))
        committed_tokens = int(state.get("committed_tokens", 0))
        active = int(state.get("active", 0))

        projected_requests = committed_requests + reserved_requests + 1
        projected_tokens = committed_tokens + reserved_tokens + reservation.estimated_total_tokens

        requests_limit = int(getattr(limit, "requests_per_minute", 0) or 0)
        tokens_limit = int(getattr(limit, "tokens_per_minute", 0) or 0)
        concurrency_limit = int(getattr(limit, "concurrency", 0) or 0)

        if requests_limit > 0 and projected_requests > requests_limit:
            return False
        if tokens_limit > 0 and projected_tokens > tokens_limit:
            return False
        if concurrency_limit > 0 and active + 1 > concurrency_limit:
            return False
        return True

    async def _increment_scope(self, redis_client: Any, scope_keys: Dict[str, str], reservation: QuotaReservation) -> None:
        pipe = redis_client.pipeline()
        for key in scope_keys.values():
            pipe.expire(key, _WINDOW_SECONDS * 2)
        pipe.incrby(scope_keys["reserved_requests"], 1)
        pipe.incrby(scope_keys["reserved_tokens"], reservation.estimated_total_tokens)
        pipe.incrby(scope_keys["active"], 1)
        await pipe.execute()

    @staticmethod
    def _limit_arg(limit: Any, name: str) -> int:
        return int(getattr(limit, name, 0) or 0)

    @staticmethod
    def _reserve_lua() -> str:
        return """
local estimated_tokens = tonumber(ARGV[7])
local provider_requests_limit = tonumber(ARGV[1])
local provider_tokens_limit = tonumber(ARGV[2])
local provider_concurrency_limit = tonumber(ARGV[3])
local model_requests_limit = tonumber(ARGV[4])
local model_tokens_limit = tonumber(ARGV[5])
local model_concurrency_limit = tonumber(ARGV[6])

local provider_reserved_requests = tonumber(redis.call('GET', KEYS[1]) or '0')
local provider_reserved_tokens = tonumber(redis.call('GET', KEYS[2]) or '0')
local provider_committed_requests = tonumber(redis.call('GET', KEYS[3]) or '0')
local provider_committed_tokens = tonumber(redis.call('GET', KEYS[4]) or '0')
local provider_active = tonumber(redis.call('GET', KEYS[5]) or '0')
local model_reserved_requests = tonumber(redis.call('GET', KEYS[6]) or '0')
local model_reserved_tokens = tonumber(redis.call('GET', KEYS[7]) or '0')
local model_committed_requests = tonumber(redis.call('GET', KEYS[8]) or '0')
local model_committed_tokens = tonumber(redis.call('GET', KEYS[9]) or '0')
local model_active = tonumber(redis.call('GET', KEYS[10]) or '0')

if provider_requests_limit > 0 and provider_committed_requests + provider_reserved_requests + 1 > provider_requests_limit then return 2 end
if provider_tokens_limit > 0 and provider_committed_tokens + provider_reserved_tokens + estimated_tokens > provider_tokens_limit then return 3 end
if provider_concurrency_limit > 0 and provider_active + 1 > provider_concurrency_limit then return 4 end
if model_requests_limit > 0 and model_committed_requests + model_reserved_requests + 1 > model_requests_limit then return 5 end
if model_tokens_limit > 0 and model_committed_tokens + model_reserved_tokens + estimated_tokens > model_tokens_limit then return 6 end
if model_concurrency_limit > 0 and model_active + 1 > model_concurrency_limit then return 7 end

redis.call('INCRBY', KEYS[1], 1)
redis.call('INCRBY', KEYS[2], estimated_tokens)
redis.call('INCRBY', KEYS[5], 1)
redis.call('INCRBY', KEYS[6], 1)
redis.call('INCRBY', KEYS[7], estimated_tokens)
redis.call('INCRBY', KEYS[10], 1)
for i = 1, 10 do redis.call('EXPIRE', KEYS[i], tonumber(ARGV[8])) end
redis.call('SET', KEYS[11], ARGV[9], 'EX', tonumber(ARGV[10]))
return 1
"""

    def _increment_in_memory(self, scope: str, reservation: QuotaReservation) -> None:
        state = self._memory.setdefault(scope, {})
        state["reserved_requests"] = int(state.get("reserved_requests", 0)) + 1
        state["reserved_tokens"] = int(state.get("reserved_tokens", 0)) + reservation.estimated_total_tokens
        state["active"] = int(state.get("active", 0)) + 1

    async def _decrement_reserved_and_increment_committed(
        self,
        redis_client: Any,
        scope_keys: Dict[str, str],
        reserved_total: int,
        actual_total: int,
    ) -> None:
        pipe = redis_client.pipeline()
        pipe.decrby(scope_keys["reserved_requests"], 1)
        pipe.decrby(scope_keys["reserved_tokens"], reserved_total)
        pipe.decrby(scope_keys["active"], 1)
        pipe.incrby(scope_keys["committed_requests"], 1)
        pipe.incrby(scope_keys["committed_tokens"], actual_total)
        pipe.expire(scope_keys["reserved_requests"], _WINDOW_SECONDS * 2)
        pipe.expire(scope_keys["reserved_tokens"], _WINDOW_SECONDS * 2)
        pipe.expire(scope_keys["committed_requests"], _WINDOW_SECONDS * 2)
        pipe.expire(scope_keys["committed_tokens"], _WINDOW_SECONDS * 2)
        pipe.expire(scope_keys["active"], _WINDOW_SECONDS * 2)
        await pipe.execute()

    async def _decrement_reserved(
        self,
        redis_client: Any,
        scope_keys: Dict[str, str],
        reserved_total: int,
    ) -> None:
        pipe = redis_client.pipeline()
        pipe.decrby(scope_keys["reserved_requests"], 1)
        pipe.decrby(scope_keys["reserved_tokens"], reserved_total)
        pipe.decrby(scope_keys["active"], 1)
        pipe.expire(scope_keys["reserved_requests"], _WINDOW_SECONDS * 2)
        pipe.expire(scope_keys["reserved_tokens"], _WINDOW_SECONDS * 2)
        pipe.expire(scope_keys["active"], _WINDOW_SECONDS * 2)
        await pipe.execute()

    def _decrement_reserved_and_increment_committed_in_memory(
        self,
        scope: str,
        reserved_total: int,
        actual_total: int,
    ) -> None:
        state = self._memory.setdefault(scope, {})
        state["reserved_requests"] = max(0, int(state.get("reserved_requests", 0)) - 1)
        state["reserved_tokens"] = max(0, int(state.get("reserved_tokens", 0)) - reserved_total)
        state["active"] = max(0, int(state.get("active", 0)) - 1)
        state["committed_requests"] = int(state.get("committed_requests", 0)) + 1
        state["committed_tokens"] = int(state.get("committed_tokens", 0)) + actual_total

    def _decrement_reserved_in_memory(self, scope: str, reserved_total: int) -> None:
        state = self._memory.setdefault(scope, {})
        state["reserved_requests"] = max(0, int(state.get("reserved_requests", 0)) - 1)
        state["reserved_tokens"] = max(0, int(state.get("reserved_tokens", 0)) - reserved_total)
        state["active"] = max(0, int(state.get("active", 0)) - 1)

    @staticmethod
    def _serialize_reservation(reservation: QuotaReservation) -> str:
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


quota_service = ProviderQuotaService()
