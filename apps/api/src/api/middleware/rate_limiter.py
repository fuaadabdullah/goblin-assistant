"""Rate limiting middleware for Goblin Assistant API."""

import asyncio
import ipaddress
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse

from ..core.contracts import ApiErrorPayload, ErrorEnvelope
from ..core.error_types import ErrorType
from ..core.redis_client import get_redis_client
from ..observability.telemetry import set_rate_limiter_degraded


def _trusted_proxy_networks() -> list[Any]:
    raw = os.getenv("TRUSTED_PROXY_CIDRS", "")
    networks: list[Any] = []
    for item in raw.split(","):
        value = item.strip()
        if not value:
            continue
        try:
            networks.append(ipaddress.ip_network(value, strict=False))
        except ValueError:
            continue
    return networks


def _is_trusted_proxy(host: str | None) -> bool:
    if not host:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(ip in network for network in _trusted_proxy_networks())


def _bucket_user_id(request: Request) -> str | None:
    """Best-effort user id for rate-limit bucketing, read directly from the
    request's bearer token instead of request.state.

    This deliberately does NOT verify the token's signature: this middleware
    runs before route dependencies (including the real auth check) resolve,
    so request.state.auth_user_id isn't set yet at this point — keying on it
    here was previously dead code. Real authorization still happens later in
    the request via the route's own auth dependency; an unparseable, expired,
    or forged token here only means the request buckets by IP below instead
    of by user, the same fallback that already applies to anonymous traffic.
    Full verification (signature + possible JWKS/auth-API network calls) is
    deliberately skipped so this stays a cheap, local check on every request.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:].strip()
    if not token:
        return None
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
    except Exception:
        return None
    subject = payload.get("sub")
    return str(subject) if subject else None


def _client_ip_from_request(request: Request) -> str:
    peer_ip = request.client.host if request.client else "unknown"
    if not _is_trusted_proxy(peer_ip):
        return peer_ip

    forwarded = request.headers.get("X-Forwarded-For")
    if not forwarded:
        return peer_ip

    candidate = forwarded.split(",")[0].strip()
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return peer_ip
    return candidate


class RateLimiter:
    """Rate limiter using Redis with in-process fallback."""

    def __init__(
        self,
        requests_per_minute: int = 100,
        requests_per_hour: int = 1000,
        environment: str | None = None,
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.environment = str(
            environment if environment is not None else os.getenv("ENVIRONMENT", "development")
        ).lower()
        self._backend_degraded = False
        self._fallback_counts: dict[str, tuple[int, float]] = {}
        self._fallback_lock = asyncio.Lock()

    def _get_client_identifier(self, request: Request) -> str:
        """Get unique client identifier from request."""
        # Prefer bucketing by the (unverified) bearer token's subject, so a
        # logged-in user's limit follows them across IPs/proxies.
        user_id = _bucket_user_id(request)
        if user_id:
            return f"user:{user_id}"

        ip = _client_ip_from_request(request)

        return f"ip:{ip}"

    async def _check_rate_limit_fallback(self, client_id: str, now: datetime) -> dict[str, Any]:
        # Redis is unreachable: fall back to in-process counters so a backend
        # outage cannot silently disable rate limiting. The fallback is
        # per-process (not shared across replicas), and we mark the limiter as
        # degraded so /api/v1/ops health consumers can alert on it.
        if not self._backend_degraded:
            self._backend_degraded = True
            try:
                set_rate_limiter_degraded(degraded=True)
            except Exception:  # pragma: no cover - metrics must never break limiting
                pass
            import structlog as _structlog

            _structlog.get_logger().warning(
                "Rate limiter backend unavailable; using in-process fallback",
                environment=self.environment,
                severity="security_warning" if self.environment == "production" else "warning",
            )
        now_ts = time.time()
        minute_window_end = now_ts + (60 - now.second)
        hour_window_end = now_ts + ((60 - now.minute) * 60 - now.second)
        minute_key = f"minute:{client_id}:{now.strftime('%Y%m%d%H%M')}"
        hour_key = f"hour:{client_id}:{now.strftime('%Y%m%d%H')}"

        async with self._fallback_lock:
            # best-effort cleanup
            expired = [k for k, (_, expiry) in self._fallback_counts.items() if expiry <= now_ts]
            for key in expired:
                self._fallback_counts.pop(key, None)

            minute_count, _ = self._fallback_counts.get(minute_key, (0, minute_window_end))
            if minute_count >= self.requests_per_minute:
                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset_at": datetime.fromtimestamp(minute_window_end).isoformat(),
                    "limit_type": "minute",
                }

            hour_count, _ = self._fallback_counts.get(hour_key, (0, hour_window_end))
            if hour_count >= self.requests_per_hour:
                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset_at": datetime.fromtimestamp(hour_window_end).isoformat(),
                    "limit_type": "hour",
                }

            self._fallback_counts[minute_key] = (minute_count + 1, minute_window_end)
            self._fallback_counts[hour_key] = (hour_count + 1, hour_window_end)
            return {
                "allowed": True,
                "remaining_minute": self.requests_per_minute - minute_count - 1,
                "remaining_hour": self.requests_per_hour - hour_count - 1,
                "limit_type": "ok",
            }

    async def check_rate_limit(self, request: Request) -> dict[str, Any]:
        """
        Check if request is within rate limits.

        Returns:
            Dict with 'allowed', 'remaining', and 'reset_at' keys
        """
        client_id = self._get_client_identifier(request)
        now = datetime.utcnow()
        try:
            redis_client = await get_redis_client()
            # Check minute window
            minute_key = f"rate_limit:minute:{client_id}:{now.strftime('%Y%m%d%H%M')}"
            minute_count = await redis_client.get(minute_key)
            minute_count = int(minute_count) if minute_count else 0

            if minute_count >= self.requests_per_minute:
                reset_at = (now + timedelta(seconds=60 - now.second)).isoformat()
                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset_at": reset_at,
                    "limit_type": "minute",
                }

            # Check hour window
            hour_key = f"rate_limit:hour:{client_id}:{now.strftime('%Y%m%d%H')}"
            hour_count = await redis_client.get(hour_key)
            hour_count = int(hour_count) if hour_count else 0

            if hour_count >= self.requests_per_hour:
                reset_at = (now + timedelta(minutes=60 - now.minute)).isoformat()
                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset_at": reset_at,
                    "limit_type": "hour",
                }

            # Increment counters
            pipe = redis_client.pipeline()
            pipe.incr(minute_key)
            pipe.expire(minute_key, 60)
            pipe.incr(hour_key)
            pipe.expire(hour_key, 3600)
            await pipe.execute()

            return {
                "allowed": True,
                "remaining_minute": self.requests_per_minute - minute_count - 1,
                "remaining_hour": self.requests_per_hour - hour_count - 1,
                "limit_type": "ok",
            }
        except Exception:
            return await self._check_rate_limit_fallback(client_id, now)

    @property
    def backend_degraded(self) -> bool:
        """Whether the Redis backend has failed over to in-process counters."""
        return self._backend_degraded

    async def __call__(self, request: Request, call_next):
        """Middleware handler."""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/api/v1/health", "/metrics"]:
            return await call_next(request)

        result = await self.check_rate_limit(request)

        if not result["allowed"]:
            request_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc).isoformat()
            return JSONResponse(
                status_code=429,
                content=ErrorEnvelope(
                    error=ApiErrorPayload(
                        code="RATE_LIMIT_EXCEEDED",
                        type=ErrorType.RATE_LIMIT,
                        message="Rate limit exceeded",
                        request_id=request_id,
                        timestamp=timestamp,
                        details={
                            "limit_type": result["limit_type"],
                            "reset_at": result["reset_at"],
                        },
                    )
                ).model_dump(exclude_none=True),
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Remaining": "0",
                    "X-Request-ID": request_id,
                },
            )

        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining-Minute"] = str(result["remaining_minute"])
        response.headers["X-RateLimit-Remaining-Hour"] = str(result["remaining_hour"])

        return response
