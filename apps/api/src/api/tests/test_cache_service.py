"""
Tests for CacheService
Tests Redis-based caching with TTL rules
"""

import pytest
import json
from unittest.mock import AsyncMock, patch

from api.services.cache_service import CacheService


@pytest.fixture
def cache_service():
    """Create CacheService instance for testing"""
    return CacheService()


class TestCacheServiceConnect:
    """Tests for cache connection management"""

    @pytest.mark.asyncio
    async def test_connect_success(self, cache_service):
        """Test successful Redis connection"""
        with patch("redis.asyncio.from_url") as mock_redis:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock()
            mock_redis.return_value = mock_client

            await cache_service.connect()

            assert cache_service._is_connected is True
            mock_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure_sets_disconnected(self, cache_service):
        """Test failed connection sets disconnected state"""
        with patch("redis.asyncio.from_url") as mock_redis:
            mock_redis.side_effect = Exception("Connection refused")

            await cache_service.connect()

            assert cache_service._is_connected is False

    @pytest.mark.asyncio
    async def test_connect_idempotent(self, cache_service):
        """Test connect doesn't reconnect if already connected"""
        with patch("redis.asyncio.from_url") as mock_redis:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock()
            mock_redis.return_value = mock_client

            await cache_service.connect()
            await cache_service.connect()

            # Should only call from_url once
            mock_redis.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_success(self, cache_service):
        """Test successful disconnection"""
        cache_service.redis_client = AsyncMock()
        cache_service._is_connected = True

        await cache_service.disconnect()

        assert cache_service._is_connected is False
        cache_service.redis_client.close.assert_called_once()


class TestCacheServiceSet:
    """Tests for cache set operations"""

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, cache_service):
        """Test setting cache value with TTL"""
        cache_service.redis_client = AsyncMock()
        cache_service._is_connected = True

        result = await cache_service.set("test_key", {"data": "value"}, ttl=3600)

        assert result is True
        cache_service.redis_client.setex.assert_called_once()
        call_args = cache_service.redis_client.setex.call_args
        assert call_args[0][0] == "test_key"
        assert call_args[0][1] == 3600

    @pytest.mark.asyncio
    async def test_set_without_ttl(self, cache_service):
        """Test setting cache value without TTL"""
        cache_service.redis_client = AsyncMock()
        cache_service._is_connected = True

        result = await cache_service.set("test_key", {"data": "value"})

        assert result is True
        cache_service.redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_auto_connects(self, cache_service):
        """Test set auto-connects if disconnected"""
        with patch("redis.asyncio.from_url") as mock_redis:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock()
            mock_client.setex = AsyncMock()
            mock_redis.return_value = mock_client

            result = await cache_service.set("key", "value", ttl=100)

            assert result is True
            mock_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_serializes_to_json(self, cache_service):
        """Test values are JSON serialized"""
        cache_service.redis_client = AsyncMock()
        cache_service._is_connected = True

        test_obj = {"nested": {"value": 123}, "list": [1, 2, 3]}
        await cache_service.set("key", test_obj)

        call_args = cache_service.redis_client.set.call_args
        serialized = call_args[0][1]
        assert json.loads(serialized) == test_obj

    @pytest.mark.asyncio
    async def test_set_redis_error_returns_false(self, cache_service):
        """Test returns False on Redis error"""
        cache_service.redis_client = AsyncMock()
        cache_service.redis_client.setex.side_effect = Exception("Redis error")
        cache_service._is_connected = True

        result = await cache_service.set("key", "value", ttl=100)

        assert result is False


class TestCacheServiceGet:
    """Tests for cache get operations"""

    @pytest.mark.asyncio
    async def test_get_existing_key(self, cache_service):
        """Test retrieving existing cache key"""
        cache_service.redis_client = AsyncMock()
        cache_service._is_connected = True

        test_value = {"data": "value"}
        cache_service.redis_client.get = AsyncMock(return_value=json.dumps(test_value).encode())

        result = await cache_service.get("test_key")

        assert result == test_value
        cache_service.redis_client.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_missing_key_returns_none(self, cache_service):
        """Test retrieving missing key returns None"""
        cache_service.redis_client = AsyncMock()
        cache_service.redis_client.get = AsyncMock(return_value=None)
        cache_service._is_connected = True

        result = await cache_service.get("missing_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_auto_connects(self, cache_service):
        """Test get auto-connects if disconnected"""
        with patch("redis.asyncio.from_url") as mock_redis:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock()
            mock_client.get = AsyncMock(return_value=None)
            mock_redis.return_value = mock_client

            await cache_service.get("key")

            mock_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_returns_none_on_error(self, cache_service):
        """Test returns None on Redis error"""
        cache_service.redis_client = AsyncMock()
        cache_service.redis_client.get.side_effect = Exception("Redis error")
        cache_service._is_connected = True

        result = await cache_service.get("key")

        assert result is None


class TestCacheServiceDelete:
    """Tests for cache delete operations"""

    @pytest.mark.asyncio
    async def test_delete_existing_key(self, cache_service):
        """Test deleting existing key"""
        cache_service.redis_client = AsyncMock()
        cache_service._is_connected = True

        result = await cache_service.delete("key")

        assert result is True
        cache_service.redis_client.delete.assert_called_once_with("key")

    @pytest.mark.asyncio
    async def test_delete_returns_false_on_error(self, cache_service):
        """Test returns False on Redis error"""
        cache_service.redis_client = AsyncMock()
        cache_service.redis_client.delete.side_effect = Exception("Redis error")
        cache_service._is_connected = True

        result = await cache_service.delete("key")

        assert result is False


class TestCacheServiceClear:
    """Tests for cache clear operations"""

    @pytest.mark.asyncio
    async def test_clear_all_cache(self, cache_service):
        """Test clearing all cache entries"""
        cache_service.redis_client = AsyncMock()
        cache_service._is_connected = True

        result = await cache_service.flush()

        assert result is True
        cache_service.redis_client.flushdb.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_returns_false_on_error(self, cache_service):
        """Test returns False on Redis error"""
        cache_service.redis_client = AsyncMock()
        cache_service.redis_client.flushdb.side_effect = Exception("Redis error")
        cache_service._is_connected = True

        result = await cache_service.flush()

        assert result is False
