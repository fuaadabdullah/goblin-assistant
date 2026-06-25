from __future__ import annotations

import pytest

from api.services.stream_state_store import HybridStreamStateStore


@pytest.mark.asyncio
async def test_hybrid_store_falls_back_to_in_memory_when_redis_unavailable(monkeypatch):
    async def _fail_redis():
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr("api.services.stream_state_store.get_redis_client", _fail_redis)

    store = HybridStreamStateStore(ttl_seconds=120)
    await store.create_stream("s1", {"source": "test"})
    await store.append_chunk("s1", {"content": "hello", "done": False})

    polled = await store.poll_stream("s1")
    assert polled is not None
    assert polled["stream_id"] == "s1"
    assert polled["chunks"][0]["content"] == "hello"
    assert polled["done"] is False


@pytest.mark.asyncio
async def test_hybrid_store_cancel_marks_done_when_fallback_active(monkeypatch):
    async def _fail_redis():
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr("api.services.stream_state_store.get_redis_client", _fail_redis)

    store = HybridStreamStateStore(ttl_seconds=120)
    await store.create_stream("s2", {"source": "test"})
    cancelled = await store.cancel_stream("s2")
    assert cancelled is True

    polled = await store.poll_stream("s2")
    assert polled is not None
    assert polled["status"] == "cancelled"
    assert polled["done"] is True


@pytest.mark.asyncio
async def test_poll_returns_none_for_unknown_stream(monkeypatch):
    async def _fail_redis():
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr("api.services.stream_state_store.get_redis_client", _fail_redis)

    store = HybridStreamStateStore(ttl_seconds=120)
    assert await store.poll_stream("missing") is None
