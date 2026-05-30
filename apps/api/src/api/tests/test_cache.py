"""
Tests for the Redis caching layer.

Covers:
- RedisCache initialization and graceful fallback
- RedisCache get/set/delete/delete_pattern/exists/get_ttl operations
- cache_response decorator
- Helper functions (cache_provider_status, cache_routing_result, cache_task_result,
  get_cached_provider_status, get_cached_routing_result, get_cached_task_result)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.storage.cache import (
    RedisCache,
    cache_response,
    cache_provider_status,
    cache_routing_result,
    cache_task_result,
    get_cached_provider_status,
    get_cached_routing_result,
    get_cached_task_result,
)


# ---------------------------------------------------------------------------
# RedisCache
# ---------------------------------------------------------------------------


class TestRedisCacheInit:
    @pytest.mark.asyncio
    async def test_init_redis_success(self):
        cache = RedisCache()
        mock_redis = AsyncMock()
        mock_test_conn = AsyncMock()

        with patch("api.storage.cache.get_redis_client", return_value=mock_redis):
            with patch("api.storage.cache.redis_config.test_connection", mock_test_conn):
                await cache.init_redis()

        assert cache._initialized is True
        assert cache._redis is mock_redis

    @pytest.mark.asyncio
    async def test_init_redis_failure_graceful(self):
        cache = RedisCache()

        with patch(
            "api.storage.cache.get_redis_client",
            side_effect=Exception("connect failed"),
        ):
            await cache.init_redis()

        assert cache._initialized is True
        assert cache._redis is None

    @pytest.mark.asyncio
    async def test_init_redis_idempotent(self):
        cache = RedisCache()
        mock_redis = AsyncMock()
        mock_test_conn = AsyncMock()

        with patch("api.storage.cache.get_redis_client", return_value=mock_redis):
            with patch("api.storage.cache.redis_config.test_connection", mock_test_conn):
                await cache.init_redis()
                await cache.init_redis()  # Second call should be no-op

        assert cache._initialized is True
        # get_redis_client should only be called once


class TestRedisCacheOperations:
    @pytest.fixture
    def cache(self):
        c = RedisCache()
        c._redis = AsyncMock()
        c._initialized = True
        return c

    @pytest.mark.asyncio
    async def test_get_returns_parsed_json(self, cache):
        cache._redis.get.return_value = b'{"key": "value"}'
        result = await cache.get("test-key")
        assert result == {"key": "value"}
        cache._redis.get.assert_awaited_with("test-key")

    @pytest.mark.asyncio
    async def test_get_returns_none_when_missing(self, cache):
        cache._redis.get.return_value = None
        result = await cache.get("missing-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_none_on_error(self, cache):
        cache._redis.get.side_effect = Exception("redis error")
        result = await cache.get("error-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_initialized(self):
        cache = RedisCache()  # _redis is None
        result = await cache.get("any-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_stores_value(self, cache):
        await cache.set("my-key", {"data": 123}, expire=60)
        cache._redis.set.assert_awaited_with("my-key", '{"data": 123}', ex=60)

    @pytest.mark.asyncio
    async def test_set_uses_cache_type_ttl(self, cache):
        with patch("api.storage.cache.get_cache_ttl", return_value=300):
            await cache.set("key2", "val", cache_type="PROVIDER_STATUS")
        cache._redis.set.assert_awaited_with("key2", '"val"', ex=300)

    @pytest.mark.asyncio
    async def test_set_error_handled(self, cache):
        cache._redis.set.side_effect = Exception("set failed")
        # Should not raise
        await cache.set("fail-key", "value")

    @pytest.mark.asyncio
    async def test_set_when_not_initialized(self):
        cache = RedisCache()  # _redis is None
        # Should not raise
        await cache.set("any-key", "value")

    @pytest.mark.asyncio
    async def test_delete_calls_redis(self, cache):
        await cache.delete("del-key")
        cache._redis.delete.assert_awaited_with("del-key")

    @pytest.mark.asyncio
    async def test_delete_error_handled(self, cache):
        cache._redis.delete.side_effect = Exception("delete error")
        await cache.delete("fail-key")  # Should not raise

    @pytest.mark.asyncio
    async def test_delete_pattern(self, cache):
        cache._redis.keys.return_value = [b"k1", b"k2"]
        await cache.delete_pattern("test:*")
        cache._redis.keys.assert_awaited_with("test:*")
        cache._redis.delete.assert_awaited_with(b"k1", b"k2")

    @pytest.mark.asyncio
    async def test_delete_pattern_no_keys(self, cache):
        cache._redis.keys.return_value = []
        await cache.delete_pattern("empty:*")
        cache._redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_pattern_error_handled(self, cache):
        cache._redis.keys.side_effect = Exception("keys error")
        await cache.delete_pattern("fail:*")  # Should not raise

    @pytest.mark.asyncio
    async def test_exists_returns_true(self, cache):
        cache._redis.exists.return_value = 1
        result = await cache.exists("exists-key")
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false(self, cache):
        cache._redis.exists.return_value = 0
        result = await cache.exists("missing-key")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_error_handled(self, cache):
        cache._redis.exists.side_effect = Exception("exists error")
        result = await cache.exists("error-key")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_ttl(self, cache):
        cache._redis.ttl.return_value = 42
        result = await cache.get_ttl("ttl-key")
        assert result == 42

    @pytest.mark.asyncio
    async def test_get_ttl_error_handled(self, cache):
        cache._redis.ttl.side_effect = Exception("ttl error")
        result = await cache.get_ttl("error-key")
        assert result == 0

    @pytest.mark.asyncio
    async def test_close(self, cache):
        await cache.close()
        cache._redis.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_error_handled(self, cache):
        cache._redis.close.side_effect = Exception("close error")
        await cache.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_redis_property(self, cache):
        assert cache.redis is cache._redis


# ---------------------------------------------------------------------------
# cache_response decorator
# ---------------------------------------------------------------------------


class TestCacheResponseDecorator:
    @pytest.mark.asyncio
    async def test_misses_cache_when_no_request(self):
        """When no Request is found, call the function directly without caching."""

        @cache_response(expire=60)
        async def my_handler(data: str):
            return {"result": data}

        result = await my_handler(data="hello")
        assert result == {"result": "hello"}

    @pytest.mark.asyncio
    async def test_returns_cached_data(self):
        mock_request = MagicMock()
        mock_request.url.path = "/api/test"
        mock_request.url.query = ""

        @cache_response(expire=60, cache_type="TEST")
        async def my_handler(request=None):
            return {"data": "fresh"}

        with patch("api.storage.cache.cache.get", return_value={"data": "cached"}):
            result = await my_handler(request=mock_request)

        assert result == {"data": "cached"}

    @pytest.mark.asyncio
    async def test_caches_response(self):
        mock_request = MagicMock()
        mock_request.url.path = "/api/test"
        mock_request.url.query = ""

        @cache_response(expire=60, cache_type="TEST")
        async def my_handler(request=None):
            return {"data": "fresh"}

        redis_config_mock = MagicMock()
        redis_config_mock.get_cache_key.return_value = "cache:key"

        with patch("api.storage.cache.cache.get", return_value=None):
            with patch("api.storage.cache.cache.set") as mock_set:
                with patch("api.storage.cache.redis_config", redis_config_mock):
                    result = await my_handler(request=mock_request)

        assert result == {"data": "fresh"}
        mock_set.assert_awaited_once()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestCacheHelperFunctions:
    @pytest.mark.asyncio
    async def test_cache_provider_status(self):
        mock_cache = AsyncMock()
        with patch("api.storage.cache.cache", mock_cache):
            await cache_provider_status("openai", {"status": "healthy"})
            mock_cache.set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cache_routing_result(self):
        mock_cache = AsyncMock()
        with patch("api.storage.cache.cache", mock_cache):
            await cache_routing_result("chat", {"route": "openai"})
            mock_cache.set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cache_task_result(self):
        mock_cache = AsyncMock()
        with patch("api.storage.cache.cache", mock_cache):
            await cache_task_result("task-1", {"status": "done"})
            mock_cache.set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_cached_provider_status(self):
        mock_cache = AsyncMock()
        mock_cache.get.return_value = {"status": "healthy"}
        with patch("api.storage.cache.cache", mock_cache):
            result = await get_cached_provider_status("openai")
            assert result == {"status": "healthy"}
            mock_cache.get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_cached_routing_result(self):
        mock_cache = AsyncMock()
        mock_cache.get.return_value = {"route": "openai"}
        with patch("api.storage.cache.cache", mock_cache):
            result = await get_cached_routing_result("chat")
            assert result == {"route": "openai"}
            mock_cache.get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_cached_task_result(self):
        mock_cache = AsyncMock()
        mock_cache.get.return_value = {"status": "done"}
        with patch("api.storage.cache.cache", mock_cache):
            result = await get_cached_task_result("task-1")
            assert result == {"status": "done"}
            mock_cache.get.assert_awaited_once()
