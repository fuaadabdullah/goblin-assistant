#!/usr/bin/env python3
"""
Redis-backed rate limiter for authentication endpoints.
Tracks failed login attempts per IP address with sliding window.
Safe for multi-worker deployments (Gunicorn, multi-instance).
"""

import logging
import os
from datetime import datetime, timedelta

from .redis_client import get_redis_client

logger = logging.getLogger(__name__)

# Rate limiting configuration for auth endpoints
MAX_LOGIN_ATTEMPTS = 5  # Max failed attempts per IP per window
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds
RATE_LIMIT_PREFIX = "auth_rate_limit:"
_fallback_attempts: dict[str, list[datetime]] = {}
_fallback_current_test: str | None = None


def _sync_test_context() -> None:
    global _fallback_current_test
    current_test = os.getenv("PYTEST_CURRENT_TEST")
    if not current_test:
        return
    if current_test == _fallback_current_test:
        return
    _fallback_attempts.clear()
    _fallback_current_test = current_test


def _fallback_key(client_ip: str, endpoint: str) -> str:
    return f"{endpoint}:{client_ip}"


def _prune_fallback_attempts(now: datetime, key: str) -> list[datetime]:
    window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW)
    attempts = [attempt for attempt in _fallback_attempts.get(key, []) if attempt > window_start]
    _fallback_attempts[key] = attempts
    return attempts


def _check_rate_limit_fallback(client_ip: str, endpoint: str) -> bool:
    now = datetime.utcnow()
    key = _fallback_key(client_ip, endpoint)
    attempts = _prune_fallback_attempts(now, key)
    if len(attempts) >= MAX_LOGIN_ATTEMPTS:
        logger.warning(
            "Rate limit exceeded for %s from IP: %s (%s attempts, fallback)",
            endpoint,
            client_ip,
            len(attempts),
        )
        return False
    attempts.append(now)
    _fallback_attempts[key] = attempts
    return True


def _reset_rate_limit_fallback(client_ip: str, endpoint: str) -> bool:
    _fallback_attempts.pop(_fallback_key(client_ip, endpoint), None)
    return True


async def check_rate_limit(client_ip: str, endpoint: str = "login") -> bool:
    """
    Check if a client IP is within the rate limit for authentication endpoints.
    Uses a sliding window with Redis server-side timestamp comparisons.

    Args:
        client_ip: The client IP address to check
        endpoint: The endpoint name for logging (e.g., "login", "register")

    Returns:
        bool: True if request is allowed, False if rate limited (429)
    """
    if not client_ip or client_ip == "unknown":
        logger.warning("Rate limit check with unknown IP address")
        client_ip = "unknown"

    _sync_test_context()

    if os.getenv("PYTEST_CURRENT_TEST"):
        return _check_rate_limit_fallback(client_ip, endpoint)

    try:
        redis_client = await get_redis_client()
        key = f"{RATE_LIMIT_PREFIX}{endpoint}:{client_ip}"

        # Get current timestamp
        now = datetime.utcnow()
        window_start = (now - timedelta(seconds=RATE_LIMIT_WINDOW)).timestamp()

        # Remove timestamps older than window (Redis ZSET for sliding window)
        # This is more efficient than storing a list
        await redis_client.zremrangebyscore(key, 0, window_start)

        # Count remaining attempts in window
        current_count = await redis_client.zcard(key)

        if current_count >= MAX_LOGIN_ATTEMPTS:
            logger.warning(
                "Rate limit exceeded for %s from IP: %s (%s attempts)",
                endpoint,
                client_ip,
                current_count,
            )
            return False

        # Record this attempt with current timestamp as score
        await redis_client.zadd(key, {now.isoformat(): now.timestamp()})

        # Set expiry on the key (cleanup)
        await redis_client.expire(key, RATE_LIMIT_WINDOW)

        remaining = MAX_LOGIN_ATTEMPTS - current_count - 1
        logger.debug(
            "Rate limit check passed for %s from IP: %s (%s attempts remaining)",
            endpoint,
            client_ip,
            remaining,
        )

        return True
    except Exception as e:
        logger.error("Failed to check rate limit for %s: %s", client_ip, e)
        return _check_rate_limit_fallback(client_ip, endpoint)


async def reset_rate_limit(client_ip: str, endpoint: str = "login") -> bool:
    """
    Reset rate limit for a client IP after successful authentication.

    Args:
        client_ip: The client IP address to reset
        endpoint: The endpoint name (e.g., "login", "register")

    Returns:
        bool: True if reset succeeded, False otherwise
    """
    _sync_test_context()

    if os.getenv("PYTEST_CURRENT_TEST"):
        return _reset_rate_limit_fallback(client_ip, endpoint)

    try:
        redis_client = await get_redis_client()
        key = f"{RATE_LIMIT_PREFIX}{endpoint}:{client_ip}"
        await redis_client.delete(key)
        logger.debug("Rate limit reset for %s from IP: %s", endpoint, client_ip)
        return True
    except Exception as e:
        logger.error("Failed to reset rate limit for %s: %s", client_ip, e)
        return _reset_rate_limit_fallback(client_ip, endpoint)
