"""Extended tests for services/stream_state_store.py — InMemoryStreamStateStore full coverage."""

from __future__ import annotations

import pytest

from api.services.stream_state_store import (
    InMemoryStreamStateStore,
    StreamKeySet,
    _keys,
    _terminal,
)

# ── Module-level helpers ──────────────────────────────────────────────────────


class TestHelpers:
    def test_terminal_completed(self):
        assert _terminal("completed") is True

    def test_terminal_failed(self):
        assert _terminal("failed") is True

    def test_terminal_cancelled(self):
        assert _terminal("cancelled") is True

    def test_non_terminal_running(self):
        assert _terminal("running") is False

    def test_non_terminal_pending(self):
        assert _terminal("pending") is False

    def test_keys_returns_streamkeyset(self):
        ks = _keys("abc-123")
        assert isinstance(ks, StreamKeySet)
        assert "abc-123" in ks.meta
        assert "abc-123" in ks.chunks

    def test_keys_meta_and_chunks_differ(self):
        ks = _keys("abc-123")
        assert ks.meta != ks.chunks


# ── InMemoryStreamStateStore ──────────────────────────────────────────────────


class TestInMemoryStreamStateStoreCreate:
    @pytest.mark.asyncio
    async def test_creates_stream_with_running_status(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("s1", {"name": "test"})
        state = store._streams["s1"]
        assert state["status"] == "running"
        assert state["done"] is False

    @pytest.mark.asyncio
    async def test_metadata_is_stored(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("s1", {"task": "chat", "user": "u1"})
        assert store._streams["s1"]["metadata"]["task"] == "chat"

    @pytest.mark.asyncio
    async def test_chunks_starts_empty(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("s1", {})
        assert store._streams["s1"]["chunks"] == []

    @pytest.mark.asyncio
    async def test_multiple_streams_independent(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("s1", {"x": 1})
        await store.create_stream("s2", {"x": 2})
        assert store._streams["s1"]["metadata"]["x"] == 1
        assert store._streams["s2"]["metadata"]["x"] == 2

    @pytest.mark.asyncio
    async def test_stream_id_in_state(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("my-stream-id", {})
        assert store._streams["my-stream-id"]["stream_id"] == "my-stream-id"


class TestInMemoryStreamStateStoreAppendChunk:
    @pytest.mark.asyncio
    async def test_chunk_appended_to_known_stream(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("s1", {})
        await store.append_chunk("s1", {"text": "hello"})
        assert len(store._streams["s1"]["chunks"]) == 1
        assert store._streams["s1"]["chunks"][0]["text"] == "hello"

    @pytest.mark.asyncio
    async def test_multiple_chunks_appended_in_order(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("s1", {})
        for i in range(5):
            await store.append_chunk("s1", {"i": i})
        chunks = store._streams["s1"]["chunks"]
        assert [c["i"] for c in chunks] == list(range(5))

    @pytest.mark.asyncio
    async def test_append_to_unknown_stream_is_noop(self):
        store = InMemoryStreamStateStore()
        await store.append_chunk("nonexistent", {"text": "ignored"})
        assert "nonexistent" not in store._streams

    @pytest.mark.asyncio
    async def test_chunk_is_copied_not_shared(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("s1", {})
        original = {"text": "hello"}
        await store.append_chunk("s1", original)
        original["text"] = "mutated"
        assert store._streams["s1"]["chunks"][0]["text"] == "hello"


class TestInMemoryStreamStateStoreMarkStatus:
    @pytest.mark.asyncio
    async def test_mark_completed(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("s1", {})
        await store.mark_status("s1", status="completed", done=True)
        assert store._streams["s1"]["status"] == "completed"
        assert store._streams["s1"]["done"] is True

    @pytest.mark.asyncio
    async def test_mark_failed(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("s1", {})
        await store.mark_status("s1", status="failed", done=True)
        assert store._streams["s1"]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_updates_merged_into_metadata(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("s1", {"key": "original"})
        await store.mark_status("s1", status="completed", done=True, updates={"error_msg": "oops"})
        assert store._streams["s1"]["metadata"]["error_msg"] == "oops"
        assert store._streams["s1"]["metadata"]["key"] == "original"

    @pytest.mark.asyncio
    async def test_mark_status_unknown_stream_is_noop(self):
        store = InMemoryStreamStateStore()
        await store.mark_status("ghost", status="done", done=True)
        assert "ghost" not in store._streams

    @pytest.mark.asyncio
    async def test_none_updates_does_not_crash(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("s1", {})
        await store.mark_status("s1", status="completed", done=True, updates=None)
        assert store._streams["s1"]["status"] == "completed"


class TestInMemoryStreamStateStorePollStream:
    @pytest.mark.asyncio
    async def test_poll_unknown_stream_returns_none(self):
        store = InMemoryStreamStateStore()
        result = await store.poll_stream("ghost")
        assert result is None

    @pytest.mark.asyncio
    async def test_poll_returns_status_and_stream_id(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("s1", {})
        result = await store.poll_stream("s1")
        assert result is not None
        assert result["stream_id"] == "s1"
        assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_poll_drains_chunks(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("s1", {})
        await store.append_chunk("s1", {"text": "a"})
        await store.append_chunk("s1", {"text": "b"})
        result = await store.poll_stream("s1")
        assert len(result["chunks"]) == 2
        # Second poll: chunks drained
        result2 = await store.poll_stream("s1")
        assert len(result2["chunks"]) == 0

    @pytest.mark.asyncio
    async def test_poll_done_true_for_terminal_status(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("s1", {})
        await store.mark_status("s1", status="completed", done=True)
        result = await store.poll_stream("s1")
        assert result["done"] is True

    @pytest.mark.asyncio
    async def test_poll_done_false_for_running_status(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("s1", {})
        result = await store.poll_stream("s1")
        assert result["done"] is False


class TestInMemoryStreamStateStoreCancelStream:
    @pytest.mark.asyncio
    async def test_cancel_known_stream_returns_true(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("s1", {})
        result = await store.cancel_stream("s1")
        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_sets_status_and_done(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("s1", {})
        await store.cancel_stream("s1")
        assert store._streams["s1"]["status"] == "cancelled"
        assert store._streams["s1"]["done"] is True

    @pytest.mark.asyncio
    async def test_cancel_unknown_stream_returns_false(self):
        store = InMemoryStreamStateStore()
        result = await store.cancel_stream("ghost")
        assert result is False

    @pytest.mark.asyncio
    async def test_cancelled_stream_poll_returns_done(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("s1", {})
        await store.cancel_stream("s1")
        result = await store.poll_stream("s1")
        assert result["done"] is True
        assert result["status"] == "cancelled"


class TestInMemoryStreamStateStoreFullLifecycle:
    @pytest.mark.asyncio
    async def test_full_happy_path(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("s1", {"task": "summarize"})
        await store.append_chunk("s1", {"text": "partial..."})
        await store.append_chunk("s1", {"text": "done."})

        result = await store.poll_stream("s1")
        assert len(result["chunks"]) == 2
        assert result["status"] == "running"
        assert result["done"] is False

        await store.mark_status("s1", status="completed", done=True, updates={"total_tokens": 42})
        result2 = await store.poll_stream("s1")
        assert result2["done"] is True
        assert result2["status"] == "completed"
        assert store._streams["s1"]["metadata"]["total_tokens"] == 42

    @pytest.mark.asyncio
    async def test_isolation_between_streams(self):
        store = InMemoryStreamStateStore()
        await store.create_stream("s1", {})
        await store.create_stream("s2", {})
        await store.append_chunk("s1", {"text": "for-s1"})
        await store.cancel_stream("s2")

        r1 = await store.poll_stream("s1")
        r2 = await store.poll_stream("s2")

        assert r1["status"] == "running"
        assert r2["status"] == "cancelled"
        assert r1["chunks"][0]["text"] == "for-s1"
        assert r2["chunks"] == []
