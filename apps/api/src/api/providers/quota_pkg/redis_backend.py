"""Redis-backed quota backend with atomic Lua-script reservation."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import redis.asyncio as redis
import structlog

from .backend import QuotaBackend
from .models import (
    _RESERVATION_TTL_SECONDS,
    _WINDOW_SECONDS,
    QuotaReservation,
    cooldown_key,
    format_snapshot,
    limit_arg,
    reservation_key,
    scope_keys,
    serialize_reservation,
    window_key,
)

logger = structlog.get_logger(__name__)


class RedisQuotaBackend(QuotaBackend):
    def __init__(self) -> None:
        self._client: Any = None
        self._failed = False
        self._last_skip_reason = ""

    @property
    def last_skip_reason(self) -> str:
        return self._last_skip_reason

    def reset(self) -> None:
        self._client = None
        self._failed = False
        self._last_skip_reason = ""

    async def get_redis_client(self) -> Any:
        """Return a connected Redis client, or None if unavailable."""
        if self._failed:
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
        if self._client is not None:
            return self._client
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self._client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                retry_on_timeout=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            await self._client.ping()
            return self._client
        except Exception as exc:  # noqa: BLE001
            self._failed = True
            logger.debug("quota_redis_unavailable", error=str(exc))
            return None

    async def reserve(
        self,
        reservation: QuotaReservation,
        provider_limit: Any,
        shared_limit: Any,
    ) -> bool:
        rc = await self.get_redis_client()
        if rc is None:
            return False  # caller should use memory backend instead
        return await self.reserve_with_client(rc, reservation, provider_limit, shared_limit)

    async def reserve_with_client(
        self,
        rc: Any,
        reservation: QuotaReservation,
        provider_limit: Any,
        shared_limit: Any,
    ) -> bool:
        self._last_skip_reason = ""

        # Re-check cooldown inside the Redis path for safety (TOCTOU guard).
        if await rc.exists(cooldown_key(reservation.provider_scope)):
            self._last_skip_reason = "provider-cooldown"
            return False
        if await rc.exists(cooldown_key(reservation.model_scope)):
            self._last_skip_reason = "model-cooldown"
            return False

        now = datetime.now(timezone.utc)
        wkey = window_key(now)
        pkeys = scope_keys(reservation.provider_scope, wkey)
        mkeys = scope_keys(reservation.model_scope, wkey)

        ok = int(
            await rc.eval(
                self._reserve_lua(),
                11,
                pkeys["reserved_requests"],
                pkeys["reserved_tokens"],
                pkeys["committed_requests"],
                pkeys["committed_tokens"],
                pkeys["active"],
                mkeys["reserved_requests"],
                mkeys["reserved_tokens"],
                mkeys["committed_requests"],
                mkeys["committed_tokens"],
                mkeys["active"],
                reservation_key(reservation.reservation_id),
                limit_arg(provider_limit, "requests_per_minute"),
                limit_arg(provider_limit, "tokens_per_minute"),
                limit_arg(provider_limit, "concurrency"),
                limit_arg(shared_limit, "requests_per_minute"),
                limit_arg(shared_limit, "tokens_per_minute"),
                limit_arg(shared_limit, "concurrency"),
                reservation.estimated_total_tokens,
                _WINDOW_SECONDS * 2,
                serialize_reservation(reservation),
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

    async def commit(
        self,
        reservation: QuotaReservation,
        *,
        actual_input_tokens: int = 0,
        actual_output_tokens: int = 0,
    ) -> None:
        rc = await self.get_redis_client()
        if rc is None:
            return
        actual_total = max(0, actual_input_tokens + actual_output_tokens)
        await self._finalize(rc, reservation, actual_total, committed=True)

    async def release(self, reservation: QuotaReservation) -> None:
        rc = await self.get_redis_client()
        if rc is None:
            return
        await self._finalize(rc, reservation, 0, committed=False)

    async def mark_rate_limited(self, scopes: List[str], cooldown_seconds: int) -> None:
        rc = await self.get_redis_client()
        if rc is None:
            return
        for scope in scopes:
            await rc.set(cooldown_key(scope), "1", ex=max(1, cooldown_seconds))

    async def can_attempt(self, provider_scope: str, model_scope: str) -> bool:
        rc = await self.get_redis_client()
        if rc is None:
            return True
        return not (
            await rc.exists(cooldown_key(provider_scope))
            or await rc.exists(cooldown_key(model_scope))
        )

    async def scope_snapshot(self, scope: str, limit: Any, wkey: str) -> Dict[str, Any]:
        rc = await self.get_redis_client()
        if rc is None:
            return format_snapshot(scope, wkey, limit, 0, 0, 0, 0, 0, 0.0)

        skeys = scope_keys(scope, wkey)
        reserved_requests = int(await rc.get(skeys["reserved_requests"]) or 0)
        reserved_tokens = int(await rc.get(skeys["reserved_tokens"]) or 0)
        committed_requests = int(await rc.get(skeys["committed_requests"]) or 0)
        committed_tokens = int(await rc.get(skeys["committed_tokens"]) or 0)
        active = int(await rc.get(skeys["active"]) or 0)
        cooldown_remaining = 0.0
        ttl = await rc.ttl(cooldown_key(scope))
        if isinstance(ttl, int) and ttl > 0:
            cooldown_remaining = float(ttl)

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
    # Private helpers
    # ------------------------------------------------------------------

    async def _finalize(
        self,
        rc: Any,
        reservation: QuotaReservation,
        actual_total: int,
        *,
        committed: bool,
    ) -> None:
        wkey = reservation.window_key
        pkeys = scope_keys(reservation.provider_scope, wkey)
        mkeys = scope_keys(reservation.model_scope, wkey)
        if committed:
            await self._decrement_reserved_and_commit(
                rc, pkeys, reservation.estimated_total_tokens, actual_total
            )
            await self._decrement_reserved_and_commit(
                rc, mkeys, reservation.estimated_total_tokens, actual_total
            )
        else:
            await self._decrement_reserved(rc, pkeys, reservation.estimated_total_tokens)
            await self._decrement_reserved(rc, mkeys, reservation.estimated_total_tokens)
        await rc.delete(reservation_key(reservation.reservation_id))

    async def _decrement_reserved_and_commit(
        self, rc: Any, skeys: Dict[str, str], reserved_total: int, actual_total: int
    ) -> None:
        pipe = rc.pipeline()
        pipe.decrby(skeys["reserved_requests"], 1)
        pipe.decrby(skeys["reserved_tokens"], reserved_total)
        pipe.decrby(skeys["active"], 1)
        pipe.incrby(skeys["committed_requests"], 1)
        pipe.incrby(skeys["committed_tokens"], actual_total)
        pipe.expire(skeys["reserved_requests"], _WINDOW_SECONDS * 2)
        pipe.expire(skeys["reserved_tokens"], _WINDOW_SECONDS * 2)
        pipe.expire(skeys["committed_requests"], _WINDOW_SECONDS * 2)
        pipe.expire(skeys["committed_tokens"], _WINDOW_SECONDS * 2)
        pipe.expire(skeys["active"], _WINDOW_SECONDS * 2)
        await pipe.execute()

    async def _decrement_reserved(
        self, rc: Any, skeys: Dict[str, str], reserved_total: int
    ) -> None:
        pipe = rc.pipeline()
        pipe.decrby(skeys["reserved_requests"], 1)
        pipe.decrby(skeys["reserved_tokens"], reserved_total)
        pipe.decrby(skeys["active"], 1)
        pipe.expire(skeys["reserved_requests"], _WINDOW_SECONDS * 2)
        pipe.expire(skeys["reserved_tokens"], _WINDOW_SECONDS * 2)
        pipe.expire(skeys["active"], _WINDOW_SECONDS * 2)
        await pipe.execute()

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
