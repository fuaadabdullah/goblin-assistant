"""Rate limiting middleware for Goblin Assistant API."""

from typing import Dict
from datetime import datetime, timedelta
from fastapi import Request
from fastapi.responses import JSONResponse
import redis.asyncio as redis


class RateLimiter:
    """Rate limiter using Redis backend."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        requests_per_minute: int = 100,
        requests_per_hour: int = 1000,
    ):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour

    def _get_client_identifier(self, request: Request) -> str:
        """Get unique client identifier from request."""
        # Try to get authenticated user ID first
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return f"ip:{ip}"

    async def check_rate_limit(self, request: Request) -> Dict[str, any]:
        """
        Check if request is within rate limits.

        Returns:
            Dict with 'allowed', 'remaining', and 'reset_at' keys
        """
        client_id = self._get_client_identifier(request)
        now = datetime.utcnow()

        # Check minute window
        minute_key = f"rate_limit:minute:{client_id}:{now.strftime('%Y%m%d%H%M')}"
        minute_count = await self.redis_client.get(minute_key)
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
        hour_count = await self.redis_client.get(hour_key)
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
        pipe = self.redis_client.pipeline()
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

    async def __call__(self, request: Request, call_next):
        """Middleware handler."""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)

        try:
            result = await self.check_rate_limit(request)
        except Exception:
            # Redis unavailable — allow request through without rate limiting
            return await call_next(request)

        if not result["allowed"]:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "limit_type": result["limit_type"],
                    "reset_at": result["reset_at"],
                },
                headers={"Retry-After": "60", "X-RateLimit-Remaining": "0"},
            )

        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining-Minute"] = str(
            result["remaining_minute"]
        )
        response.headers["X-RateLimit-Remaining-Hour"] = str(result["remaining_hour"])

        return response
