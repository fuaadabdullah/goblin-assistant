"""Tests for CacheService in-process hit/miss counters."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.services.cache_service import CacheService


@pytest.fixture
def svc() -> CacheService:
    s = CacheService()
    s._is_connected = True
    s.redis_client = MagicMock()
    return s


async def _mock_get(redis_client, key, value):
    """Helper: configure redis_client.get to return a JSON-serialised value."""
    redis_client.get = AsyncMock(return_value=json.dumps(value).encode())


async def _mock_miss(redis_client):
    redis_client.get = AsyncMock(return_value=None)


@pytest.mark.asyncio
async def test_hit_increments_counter(svc):
    svc.reset_counters()
    await _mock_get(svc.redis_client, "k", {"x": 1})
    await svc.get("k")
    await svc.get("k")
    assert svc._hit_count == 2
    assert svc._miss_count == 0


@pytest.mark.asyncio
async def test_miss_increments_counter(svc):
    svc.reset_counters()
    await _mock_miss(svc.redis_client)
    await svc.get("k")
    assert svc._miss_count == 1
    assert svc._hit_count == 0


@pytest.mark.asyncio
async def test_get_hit_rate_correct_fraction(svc):
    svc.reset_counters()
    await _mock_get(svc.redis_client, "k", 1)
    await svc.get("k")
    await svc.get("k")
    await svc.get("k")
    await _mock_miss(svc.redis_client)
    await svc.get("k")
    rate = svc.get_hit_rate()
    assert rate["hits"] == 3
    assert rate["misses"] == 1
    assert rate["total"] == 4
    assert abs(rate["rate"] - 0.75) < 0.001


@pytest.mark.asyncio
async def test_get_hit_rate_zero_when_no_calls(svc):
    svc.reset_counters()
    rate = svc.get_hit_rate()
    assert rate["rate"] == 0.0
    assert rate["total"] == 0


def test_reset_counters_clears_state(svc):
    svc._hit_count = 99
    svc._miss_count = 42
    svc.reset_counters()
    assert svc._hit_count == 0
    assert svc._miss_count == 0


@pytest.mark.asyncio
async def test_counters_not_incremented_on_redis_error(svc):
    svc.reset_counters()
    svc.redis_client.get = AsyncMock(side_effect=Exception("Redis down"))
    await svc.get("k")
    assert svc._hit_count == 0
    assert svc._miss_count == 0
