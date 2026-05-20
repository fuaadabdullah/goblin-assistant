"""
Cache service for Write-Time Intelligence
Implements TTL-based caching with Redis for different message types
"""

import os
import json
import asyncio
import structlog
from typing import Any, Optional, Dict, Union
import redis.asyncio as redis
from datetime import datetime, timedelta

logger = structlog.get_logger()


class CacheService:
    """Service for managing Redis-based caching with TTL rules"""
    
    def __init__(self):
        self.redis_client = None
        self._redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._is_connected = False
    
    async def connect(self):
        """Initialize Redis connection"""
        if self._is_connected:
            return
        
        try:
            self.redis_client = redis.from_url(self._redis_url)
            # Test connection
            await self.redis_client.ping()
            self._is_connected = True
            logger.info("Cache service connected to Redis", url=self._redis_url)
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            self._is_connected = False
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self._is_connected = False
            logger.info("Cache service disconnected from Redis")
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set a value in cache with optional TTL
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds
        
        Returns:
            True if successful, False otherwise
        """
        if not self._is_connected:
            await self.connect()
            if not self._is_connected:
                return False
        
        try:
            # Serialize value to JSON
            serialized_value = json.dumps(value, default=str)
            
            if ttl:
                await self.redis_client.setex(key, ttl, serialized_value)
            else:
                await self.redis_client.set(key, serialized_value)
            
            logger.debug("Cache set", key=key, ttl=ttl)
            return True
            
        except Exception as e:
            logger.error("Cache set failed", key=key, error=str(e))
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache
        
        Args:
            key: Cache key
        
        Returns:
            Deserialized value if found, None otherwise
        """
        if not self._is_connected:
            await self.connect()
            if not self._is_connected:
                return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                deserialized = json.loads(value)
                logger.debug("Cache hit", key=key)
                return deserialized
            else:
                logger.debug("Cache miss", key=key)
                return None
                
        except Exception as e:
            logger.error("Cache get failed", key=key, error=str(e))
            return None
    
    async def delete(self, key: str) -> bool:
        """
        Delete a key from cache
        
        Args:
            key: Cache key
        
        Returns:
            True if successful, False otherwise
        """
        if not self._is_connected:
            return False
        
        try:
            result = await self.redis_client.delete(key)
            logger.debug("Cache delete", key=key, deleted=bool(result))
            return bool(result)
        except Exception as e:
            logger.error("Cache delete failed", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache
        
        Args:
            key: Cache key
        
        Returns:
            True if key exists, False otherwise
        """
        if not self._is_connected:
            return False
        
        try:
            result = await self.redis_client.exists(key)
            return bool(result)
        except Exception as e:
            logger.error("Cache exists check failed", key=key, error=str(e))
            return False
    
    async def ttl(self, key: str) -> int:
        """
        Get remaining TTL for a key
        
        Args:
            key: Cache key
        
        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist
        """
        if not self._is_connected:
            return -2
        
        try:
            return await self.redis_client.ttl(key)
        except Exception as e:
            logger.error("Cache TTL check failed", key=key, error=str(e))
            return -2
    
    async def keys(self, pattern: str) -> list:
        """
        Get keys matching a pattern
        
        Args:
            pattern: Redis pattern (e.g., "message:*")
        
        Returns:
            List of matching keys
        """
        if not self._is_connected:
            return []
        
        try:
            keys = await self.redis_client.keys(pattern)
            return [key.decode() for key in keys]
        except Exception as e:
            logger.error("Cache keys search failed", pattern=pattern, error=str(e))
            return []
    
    async def flush(self) -> bool:
        """
        Flush all cache data (use with caution)
        
        Returns:
            True if successful, False otherwise
        """
        if not self._is_connected:
            return False
        
        try:
            await self.redis_client.flushdb()
            logger.info("Cache flushed")
            return True
        except Exception as e:
            logger.error("Cache flush failed", error=str(e))
            return False
    
    # TTL-based convenience methods
    
    async def set_short_term(self, key: str, value: Any, minutes: int = 5) -> bool:
        """Set value with short-term TTL (minutes)"""
        return await self.set(key, value, ttl=minutes * 60)
    
    async def set_medium_term(self, key: str, value: Any, hours: int = 1) -> bool:
        """Set value with medium-term TTL (hours)"""
        return await self.set(key, value, ttl=hours * 3600)
    
    async def set_long_term(self, key: str, value: Any, days: int = 7) -> bool:
        """Set value with long-term TTL (days)"""
        return await self.set(key, value, ttl=days * 86400)
    
    # Message-specific caching methods
    
    async def cache_message(
        self, 
        message_id: str, 
        message_data: Dict[str, Any], 
        duration: str = "short"
    ) -> bool:
        """
        Cache a message with appropriate TTL based on duration
        
        Args:
            message_id: Message identifier
            message_data: Message data to cache
            duration: "short", "medium", or "long"
        
        Returns:
            True if cached successfully
        """
        key = f"message:{message_id}"
        
        if duration == "short":
            return await self.set_short_term(key, message_data, minutes=5)
        elif duration == "medium":
            return await self.set_medium_term(key, message_data, hours=1)
        elif duration == "long":
            return await self.set_long_term(key, message_data, days=7)
        else:
            return await self.set(key, message_data, ttl=600)  # 10 minutes default
    
    async def get_cached_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get cached message data"""
        key = f"message:{message_id}"
        return await self.get(key)
    
    async def cache_conversation_context(
        self, 
        conversation_id: str, 
        context_data: Dict[str, Any]
    ) -> bool:
        """Cache conversation context with medium-term TTL"""
        key = f"context:{conversation_id}"
        return await self.set_medium_term(key, context_data, hours=2)
    
    async def get_cached_context(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get cached conversation context"""
        key = f"context:{conversation_id}"
        return await self.get(key)
    
    async def cache_user_preferences(
        self, 
        user_id: str, 
        preferences: Dict[str, Any]
    ) -> bool:
        """Cache user preferences with long-term TTL"""
        key = f"preferences:{user_id}"
        return await self.set_long_term(key, preferences, days=30)
    
    async def get_cached_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user preferences"""
        key = f"preferences:{user_id}"
        return await self.get(key)
    
    # Cache management and monitoring
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics and health information"""
        if not self._is_connected:
            return {"status": "disconnected", "error": "Redis not connected"}
        
        try:
            info = await self.redis_client.info()
            
            # Get key counts by pattern
            message_keys = await self.keys("message:*")
            context_keys = await self.keys("context:*")
            preference_keys = await self.keys("preferences:*")
            
            return {
                "status": "connected",
                "redis_info": {
                    "used_memory_human": info.get("used_memory_human", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                },
                "cache_stats": {
                    "total_keys": len(message_keys) + len(context_keys) + len(preference_keys),
                    "message_keys": len(message_keys),
                    "context_keys": len(context_keys),
                    "preference_keys": len(preference_keys),
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get cache stats", error=str(e))
            return {"status": "error", "error": str(e)}
    
    async def cleanup_expired_keys(self) -> Dict[str, Any]:
        """Clean up expired keys and return cleanup stats"""
        if not self._is_connected:
            return {"status": "disconnected", "cleaned_keys": 0}
        
        try:
            # Redis automatically handles TTL expiration, but we can force cleanup
            await self.redis_client.execute_command("MEMORY PURGE")
            
            # Get stats before and after
            stats_before = await self.get_cache_stats()
            
            return {
                "status": "success",
                "message": "Cache cleanup completed",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Cache cleanup failed", error=str(e))
            return {"status": "error", "error": str(e)}


# Global cache service instance
cache_service = CacheService()


# Initialize cache service on import
async def init_cache_service():
    """Initialize the global cache service"""
    await cache_service.connect()


# Cleanup function
async def cleanup_cache_service():
    """Cleanup the global cache service"""
    await cache_service.disconnect()