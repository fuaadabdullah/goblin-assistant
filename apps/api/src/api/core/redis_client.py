#!/usr/bin/env python3
"""
Singleton Redis client for shared access across the API
Follows the same pattern as CacheManager but provides a single reusable connection
"""

import asyncio
import logging
import os
from typing import Optional
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Global singleton instance
_redis_client: Optional[redis.Redis] = None
_redis_lock = asyncio.Lock()


async def get_redis_client() -> redis.Redis:
    """
    Get or create the singleton Redis client.
    Uses lazy initialization with lock to ensure thread-safe singleton creation.
    """
    global _redis_client
    
    if _redis_client is None:
        async with _redis_lock:
            if _redis_client is None:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                try:
                    _redis_client = redis.from_url(
                        redis_url,
                        encoding="utf-8",
                        decode_responses=True,
                        retry_on_timeout=True,
                        socket_connect_timeout=5,
                        socket_timeout=5,
                    )
                    # Test connection
                    await _redis_client.ping()
                    logger.info("Redis client connection established")
                except Exception as e:
                    logger.error(f"Failed to connect to Redis: {e}")
                    _redis_client = None
                    raise
    
    return _redis_client


async def close_redis_client():
    """Close the Redis connection"""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis client connection closed")
