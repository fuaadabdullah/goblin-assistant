"""
Redis Configuration for Goblin Assistant Backend

This module provides Redis connection configuration and utilities
for caching, session storage, and rate limiting in production.
"""

import os
from typing import Optional
from redis.asyncio import Redis
from redis.exceptions import ConnectionError, TimeoutError


class RedisConfig:
    """Redis configuration class with production-ready settings."""

    def __init__(self):
        # Redis connection settings
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", 6379))
        self.db = int(os.getenv("REDIS_DB", 0))
        self.password = os.getenv("REDIS_PASSWORD", None)
        self.url = os.getenv("REDIS_URL", None)

        # Connection pool settings
        self.max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", 50))
        self.socket_timeout = float(os.getenv("REDIS_SOCKET_TIMEOUT", 5.0))
        self.socket_connect_timeout = float(os.getenv("REDIS_CONNECT_TIMEOUT", 5.0))
        self.retry_on_timeout = (
            os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true"
        )

        # Production settings
        self.health_check_interval = int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", 30))
        self.socket_keepalive = (
            os.getenv("REDIS_SOCKET_KEEPALIVE", "true").lower() == "true"
        )
        self.socket_keepalive_options = {}

        # Cache settings
        self.default_ttl = int(os.getenv("REDIS_DEFAULT_TTL", 3600))  # 1 hour
        self.cache_prefix = os.getenv("REDIS_CACHE_PREFIX", "goblin_assistant:")

    def get_redis_url(self) -> str:
        """Get Redis URL for connection."""
        if self.url:
            return self.url

        password_part = f":{self.password}@" if self.password else ""
        return f"redis://{password_part}{self.host}:{self.port}/{self.db}"

    def get_redis_client(self) -> Redis:
        """Create and return Redis client instance."""
        return Redis.from_url(
            self.get_redis_url(),
            max_connections=self.max_connections,
            socket_timeout=self.socket_timeout,
            socket_connect_timeout=self.socket_connect_timeout,
            retry_on_timeout=self.retry_on_timeout,
            health_check_interval=self.health_check_interval,
            socket_keepalive=self.socket_keepalive,
            socket_keepalive_options=self.socket_keepalive_options,
            decode_responses=True,  # Automatically decode byte responses to strings
        )

    async def test_connection(self, redis_client: Redis) -> bool:
        """Test Redis connection."""
        try:
            await redis_client.ping()
            return True
        except (ConnectionError, TimeoutError) as e:
            print(f"Redis connection test failed: {e}")
            return False

    def get_cache_key(self, key: str) -> str:
        """Generate cache key with prefix."""
        return f"{self.cache_prefix}{key}"

    def get_session_key(self, session_id: str) -> str:
        """Generate session key with prefix."""
        return self.get_cache_key(f"session:{session_id}")

    def get_rate_limit_key(self, identifier: str, window: str = "minute") -> str:
        """Generate rate limit key with prefix."""
        return self.get_cache_key(f"rate_limit:{identifier}:{window}")


# Global Redis configuration instance
redis_config = RedisConfig()


async def get_redis_client() -> Redis:
    """Get Redis client instance for use in the application."""
    return redis_config.get_redis_client()


async def test_redis_connection() -> bool:
    """Test Redis connection and return status."""
    redis_client = await get_redis_client()
    try:
        return await redis_config.test_connection(redis_client)
    finally:
        await redis_client.close()


# Cache key constants
CACHE_KEYS = {
    "PROVIDER_STATUS": "provider_status",
    "ROUTING_CACHE": "routing_cache",
    "USER_SESSIONS": "user_sessions",
    "RATE_LIMITS": "rate_limits",
    "TASK_RESULTS": "task_results",
}


def get_cache_ttl(cache_type: str) -> int:
    """Get appropriate TTL for different cache types."""
    ttl_map = {
        "PROVIDER_STATUS": 300,  # 5 minutes
        "ROUTING_CACHE": 600,  # 10 minutes
        "USER_SESSIONS": 86400,  # 24 hours
        "RATE_LIMITS": 60,  # 1 minute
        "TASK_RESULTS": 1800,  # 30 minutes
    }
    return ttl_map.get(cache_type, redis_config.default_ttl)
