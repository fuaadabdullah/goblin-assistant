"""
Redis caching layer for Goblin Assistant

Updated to use production-ready Redis configuration.
"""

import json
from typing import Any, Optional, Union, Callable
from functools import wraps
from fastapi import Request, Response

# Import our production Redis configuration
from ..config.redis_config import (
    redis_config,
    get_redis_client,
    get_cache_ttl,
    CACHE_KEYS,
)


class RedisCache:
    """Production-ready Redis cache with proper error handling and configuration."""

    def __init__(self):
        self._redis = None
        self._initialized = False

    @property
    def redis(self):
        """Access to the Redis client"""
        return self._redis

    async def init_redis(self):
        """Initialize Redis connection with production settings"""
        if self._initialized:
            return

        try:
            self._redis = await get_redis_client()
            # Test the connection
            await redis_config.test_connection(self._redis)
            print("✅ Redis cache initialized successfully")
            self._initialized = True
        except Exception as e:
            print(f"⚠️  Redis initialization failed: {e}")
            print("   Continuing without Redis cache - performance may be reduced")
            self._redis = None
            self._initialized = True

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with error handling"""
        if not self._redis:
            return None
        try:
            value = await self._redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Redis get error for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None,
        cache_type: str = "DEFAULT",
    ):
        """Set value in cache with configurable TTL"""
        if not self._redis:
            return
        try:
            # Use cache-specific TTL or provided expire time
            ttl = expire or get_cache_ttl(cache_type)
            await self._redis.set(key, json.dumps(value), ex=ttl)
        except Exception as e:
            print(f"Redis set error for key {key}: {e}")

    async def delete(self, key: str):
        """Delete value from cache with error handling"""
        if not self._redis:
            return
        try:
            await self._redis.delete(key)
        except Exception as e:
            print(f"Redis delete error for key {key}: {e}")

    async def delete_pattern(self, pattern: str):
        """Delete keys matching pattern"""
        if not self._redis:
            return
        try:
            keys = await self._redis.keys(pattern)
            if keys:
                await self._redis.delete(*keys)
        except Exception as e:
            print(f"Redis delete pattern error for {pattern}: {e}")

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self._redis:
            return False
        try:
            return await self._redis.exists(key) == 1
        except Exception as e:
            print(f"Redis exists error for key {key}: {e}")
            return False

    async def get_ttl(self, key: str) -> int:
        """Get remaining TTL for key"""
        if not self._redis:
            return 0
        try:
            return await self._redis.ttl(key)
        except Exception as e:
            print(f"Redis TTL error for key {key}: {e}")
            return 0

    async def close(self):
        """Close Redis connection gracefully"""
        if self._redis:
            try:
                await self._redis.close()
                print("✅ Redis cache closed successfully")
            except Exception as e:
                print(f"Redis close error: {e}")


# Global cache instance
cache = RedisCache()


def cache_response(expire: Optional[int] = None, cache_type: str = "DEFAULT"):
    """Decorator to cache API responses with production settings"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request object to generate key
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                # Try finding request in kwargs
                request = kwargs.get("request")

            if request:
                # Generate cache key with proper prefix and cache type
                cache_key = redis_config.get_cache_key(
                    f"{cache_type}:{request.url.path}:{request.url.query}"
                )

                # Check cache
                cached_data = await cache.get(cache_key)
                if cached_data:
                    return cached_data

            # Execute function
            response = await func(*args, **kwargs)

            # Cache response with appropriate TTL
            if request and response:
                await cache.set(
                    cache_key, response, expire=expire, cache_type=cache_type
                )

            return response

        return wrapper

    return decorator


async def cache_provider_status(provider_name: str, status: dict):
    """Cache provider status with appropriate TTL"""
    cache_key = redis_config.get_cache_key(
        f"{CACHE_KEYS['PROVIDER_STATUS']}:{provider_name}"
    )
    await cache.set(cache_key, status, cache_type="PROVIDER_STATUS")


async def cache_routing_result(task_type: str, result: dict):
    """Cache routing results with appropriate TTL"""
    cache_key = redis_config.get_cache_key(f"{CACHE_KEYS['ROUTING_CACHE']}:{task_type}")
    await cache.set(cache_key, result, cache_type="ROUTING_CACHE")


async def cache_task_result(task_id: str, result: dict):
    """Cache task results with appropriate TTL"""
    cache_key = redis_config.get_cache_key(f"{CACHE_KEYS['TASK_RESULTS']}:{task_id}")
    await cache.set(cache_key, result, cache_type="TASK_RESULTS")


async def get_cached_provider_status(provider_name: str) -> Optional[dict]:
    """Get cached provider status"""
    cache_key = redis_config.get_cache_key(
        f"{CACHE_KEYS['PROVIDER_STATUS']}:{provider_name}"
    )
    return await cache.get(cache_key)


async def get_cached_routing_result(task_type: str) -> Optional[dict]:
    """Get cached routing result"""
    cache_key = redis_config.get_cache_key(f"{CACHE_KEYS['ROUTING_CACHE']}:{task_type}")
    return await cache.get(cache_key)


async def get_cached_task_result(task_id: str) -> Optional[dict]:
    """Get cached task result"""
    cache_key = redis_config.get_cache_key(f"{CACHE_KEYS['TASK_RESULTS']}:{task_id}")
    return await cache.get(cache_key)
