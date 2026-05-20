#!/usr/bin/env python3
"""
Redis-backed CSRF token manager for stateless, distributed CSRF protection.
Tokens are one-time use and expire after 1 hour by default.
Safe for multi-worker deployments (Gunicorn, multi-instance).
"""

import secrets
import logging
from datetime import datetime, timedelta
from .redis_client import get_redis_client

logger = logging.getLogger(__name__)

# CSRF token configuration
CSRF_TOKEN_TTL = 3600  # 1 hour in seconds
CSRF_TOKEN_PREFIX = "csrf_token:"

# In-memory fallback for environments where Redis is unavailable.
# Format: {token: expiry_datetime_utc}
_csrf_fallback_store: dict[str, datetime] = {}


def _cleanup_fallback_store(now: datetime) -> None:
    expired = [token for token, expiry in _csrf_fallback_store.items() if expiry <= now]
    for token in expired:
        _csrf_fallback_store.pop(token, None)


async def generate_csrf_token() -> str:
    """
    Generate a new CSRF token and store it in Redis with 1-hour TTL.
    
    Returns:
        str: A cryptographically secure CSRF token
    """
    # Generate token using secrets (cryptographically secure)
    token = secrets.token_urlsafe(32)

    try:
        redis_client = await get_redis_client()
        key = f"{CSRF_TOKEN_PREFIX}{token}"
        await redis_client.set(key, "1", ex=CSRF_TOKEN_TTL)
        logger.debug(f"Generated CSRF token in Redis (expires in {CSRF_TOKEN_TTL}s)")
        return token
    except Exception as e:
        # Degrade gracefully: keep auth functional even when Redis is down.
        now = datetime.utcnow()
        _cleanup_fallback_store(now)
        _csrf_fallback_store[token] = now + timedelta(seconds=CSRF_TOKEN_TTL)
        logger.warning(
            "Redis unavailable for CSRF generation; using in-memory fallback",
            extra={"error": str(e)},
        )
        return token


async def validate_csrf_token(token: str) -> bool:
    """
    Validate a CSRF token by checking Redis and deleting it (one-time use).
    
    Args:
        token: The CSRF token to validate
        
    Returns:
        bool: True if token is valid and deleted, False otherwise
    """
    if not token:
        logger.debug("CSRF validation failed: token is empty")
        return False
    
    try:
        redis_client = await get_redis_client()
        key = f"{CSRF_TOKEN_PREFIX}{token}"
        
        # Use pipeline to check and delete atomically
        pipe = redis_client.pipeline()
        pipe.exists(key)
        pipe.delete(key)
        results = await pipe.execute()
        
        exists = results[0] > 0
        if exists:
            logger.debug("CSRF token validated and deleted (one-time use)")
            return True
        else:
            logger.debug("CSRF validation failed: token not found or already used")
            return False
    except Exception as e:
        # Fallback validation path when Redis is unavailable.
        now = datetime.utcnow()
        _cleanup_fallback_store(now)
        expiry = _csrf_fallback_store.pop(token, None)
        if expiry and expiry > now:
            logger.warning(
                "Redis unavailable for CSRF validation; accepted fallback token",
                extra={"error": str(e)},
            )
            return True

        logger.error(f"Failed to validate CSRF token: {e}")
        return False
