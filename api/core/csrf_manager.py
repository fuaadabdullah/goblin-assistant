#!/usr/bin/env python3
"""
Redis-backed CSRF token manager for stateless, distributed CSRF protection.
Tokens are one-time use and expire after 1 hour by default.
Safe for multi-worker deployments (Gunicorn, multi-instance).
"""

import secrets
import logging
from .redis_client import get_redis_client

logger = logging.getLogger(__name__)

# CSRF token configuration
CSRF_TOKEN_TTL = 3600  # 1 hour in seconds
CSRF_TOKEN_PREFIX = "csrf_token:"


async def generate_csrf_token() -> str:
    """
    Generate a new CSRF token and store it in Redis with 1-hour TTL.
    
    Returns:
        str: A cryptographically secure CSRF token
    """
    try:
        redis_client = await get_redis_client()
        
        # Generate token using secrets (cryptographically secure)
        token = secrets.token_urlsafe(32)
        
        # Store in Redis with TTL
        key = f"{CSRF_TOKEN_PREFIX}{token}"
        await redis_client.set(key, "1", ex=CSRF_TOKEN_TTL)
        
        logger.debug(f"Generated CSRF token (expires in {CSRF_TOKEN_TTL}s)")
        return token
    except Exception as e:
        logger.error(f"Failed to generate CSRF token: {e}")
        raise


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
        logger.error(f"Failed to validate CSRF token: {e}")
        return False
