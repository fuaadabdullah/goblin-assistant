"""
Caching module for secrets adapters.

Provides LRU cache with TTL (time-to-live) support for secrets data.
"""

import asyncio
import time
from typing import Dict, Optional, Any, Tuple
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


class TTLCache:
    """
    Thread-safe LRU cache with TTL support.

    Automatically evicts expired entries and maintains LRU ordering.
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize TTL cache.

        Args:
            max_size: Maximum number of entries before eviction
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start background cleanup task."""
        if not self._running:
            self._running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.debug("TTL cache cleanup task started")

    async def stop(self) -> None:
        """Stop background cleanup task."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        logger.debug("TTL cache cleanup task stopped")

    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired entries."""
        while self._running:
            try:
                await asyncio.sleep(60)  # Cleanup every minute
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")

    async def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                key
                for key, (_, expires_at) in self._cache.items()
                if expires_at <= current_time
            ]

            for key in expired_keys:
                del self._cache[key]
                logger.debug(f"Evicted expired cache entry: {key}")

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            if key not in self._cache:
                return None

            value, expires_at = self._cache[key]

            # Check if expired
            if time.time() > expires_at:
                del self._cache[key]
                logger.debug(f"Cache entry expired: {key}")
                return None

            # Move to end (LRU)
            self._cache.move_to_end(key)
            return value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        async with self._lock:
            expires_at = time.time() + (ttl or self.default_ttl)

            # Remove existing entry to update LRU order
            if key in self._cache:
                del self._cache[key]

            # Add new entry
            self._cache[key] = (value, expires_at)

            # Evict oldest entries if over limit
            while len(self._cache) > self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                logger.debug(f"Evicted LRU cache entry: {oldest_key}")

    async def delete(self, key: str) -> bool:
        """
        Delete entry from cache.

        Args:
            key: Cache key

        Returns:
            True if entry was deleted, False if not found
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        """Clear all entries from cache."""
        async with self._lock:
            self._cache.clear()
            logger.debug("Cache cleared")

    async def size(self) -> int:
        """Get current cache size."""
        async with self._lock:
            return len(self._cache)

    async def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        async with self._lock:
            current_time = time.time()
            expired_count = sum(
                1
                for _, expires_at in self._cache.values()
                if expires_at <= current_time
            )

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "default_ttl": self.default_ttl,
                "expired_entries": expired_count,
                "active_entries": len(self._cache) - expired_count,
            }


class SecretCache:
    """
    Specialized cache for secrets with built-in invalidation.
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize secret cache.

        Args:
            max_size: Maximum number of cached secrets
            default_ttl: Default time-to-live in seconds
        """
        self.ttl_cache = TTLCache(max_size, default_ttl)
        self._path_to_keys: Dict[str, set] = {}  # Maps secret path to cached keys

    async def start(self) -> None:
        """Start the cache."""
        await self.ttl_cache.start()

    async def stop(self) -> None:
        """Stop the cache."""
        await self.ttl_cache.stop()

    async def get_secret(
        self, path: str, version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached secret.

        Args:
            path: Secret path
            version: Secret version

        Returns:
            Cached secret data or None
        """
        key = self._make_key(path, version)
        return await self.ttl_cache.get(key)

    async def set_secret(
        self,
        path: str,
        secret_data: Dict[str, Any],
        version: Optional[int] = None,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Cache secret data.

        Args:
            path: Secret path
            secret_data: Secret data to cache
            version: Secret version
            ttl: Time-to-live in seconds
        """
        key = self._make_key(path, version)
        await self.ttl_cache.set(key, secret_data, ttl)

        # Track path mapping for invalidation
        if path not in self._path_to_keys:
            self._path_to_keys[path] = set()
        self._path_to_keys[path].add(key)

    async def invalidate_path(self, path: str) -> None:
        """
        Invalidate all cached entries for a given path.

        Args:
            path: Secret path to invalidate
        """
        if path in self._path_to_keys:
            keys_to_delete = self._path_to_keys[path].copy()

            for key in keys_to_delete:
                await self.ttl_cache.delete(key)

            del self._path_to_keys[path]
            logger.debug(f"Invalidated cache entries for path: {path}")

    async def invalidate_key(self, path: str, version: Optional[int] = None) -> None:
        """
        Invalidate a specific cached entry.

        Args:
            path: Secret path
            version: Secret version
        """
        key = self._make_key(path, version)
        await self.ttl_cache.delete(key)

        # Remove from path mapping if it exists
        if path in self._path_to_keys and key in self._path_to_keys[path]:
            self._path_to_keys[path].discard(key)
            if not self._path_to_keys[path]:  # Remove empty set
                del self._path_to_keys[path]

        logger.debug(f"Invalidated cache entry: {key}")

    async def clear(self) -> None:
        """Clear all cached secrets."""
        await self.ttl_cache.clear()
        self._path_to_keys.clear()
        logger.debug("Secret cache cleared")

    async def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        base_stats = await self.ttl_cache.stats()
        base_stats.update(
            {
                "tracked_paths": len(self._path_to_keys),
                "total_path_keys": sum(
                    len(keys) for keys in self._path_to_keys.values()
                ),
            }
        )
        return base_stats

    @staticmethod
    def _make_key(path: str, version: Optional[int] = None) -> str:
        """Create cache key from path and version."""
        if version is not None:
            return f"{path}:{version}"
        return path
