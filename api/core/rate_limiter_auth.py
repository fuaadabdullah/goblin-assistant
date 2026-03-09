#!/usr/bin/env python3
"""
Redis-backed rate limiter for authentication endpoints.
Tracks failed login attempts per IP address with sliding window.
Safe for multi-worker deployments (Gunicorn, multi-instance).
"""

import logging
from datetime import datetime, timedelta
from .redis_client import get_redis_client

logger = logging.getLogger(__name__)

# Rate limiting configuration for auth endpoints
MAX_LOGIN_ATTEMPTS = 5  # Max failed attempts per IP per window
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds
RATE_LIMIT_PREFIX = "auth_rate_limit:"


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
                f"Rate limit exceeded for {endpoint} from IP: {client_ip} "
                f"({current_count} attempts)"
            )
            return False
        
        # Record this attempt with current timestamp as score
        await redis_client.zadd(key, {now.isoformat(): now.timestamp()})
        
        # Set expiry on the key (cleanup)
        await redis_client.expire(key, RATE_LIMIT_WINDOW)
        
        remaining = MAX_LOGIN_ATTEMPTS - current_count - 1
        logger.debug(
            f"Rate limit check passed for {endpoint} from IP: {client_ip} "
            f"({remaining} attempts remaining)"
        )
        
        return True
    except Exception as e:
        logger.error(f"Failed to check rate limit for {client_ip}: {e}")
        # Fail open in case of Redis error (allow request, log error)
        return True


async def reset_rate_limit(client_ip: str, endpoint: str = "login") -> bool:
    """
    Reset rate limit for a client IP after successful authentication.
    
    Args:
        client_ip: The client IP address to reset
        endpoint: The endpoint name (e.g., "login", "register")
        
    Returns:
        bool: True if reset succeeded, False otherwise
    """
    try:
        redis_client = await get_redis_client()
        key = f"{RATE_LIMIT_PREFIX}{endpoint}:{client_ip}"
        await redis_client.delete(key)
        logger.debug(f"Rate limit reset for {endpoint} from IP: {client_ip}")
        return True
    except Exception as e:
        logger.error(f"Failed to reset rate limit for {client_ip}: {e}")
        return False
