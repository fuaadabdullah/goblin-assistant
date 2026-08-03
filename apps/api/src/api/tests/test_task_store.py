"""Tests for TaskStore — in-memory and SQLAlchemy-backed database implementations.

Strategy
--------
In-memory tests instantiate TaskStore directly with use_db=False (the default).
DB backend tests spin up a real SQLite in-memory engine, create all tables via
Base.metadata, and patch get_db_context to inject sessions from that engine.
This exercises the actual SQLAlchemy queries without touching the filesystem.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_in_memory_store():
    """Return a TaskStore with the in-memory backend (use_db=False)."""
    from api.storage.tasks import TaskStore

    with patch.object(TaskStore, "_init_db"):
        store = TaskStore.__new__(TaskStore)
        store.use_db = False
        store._in_memory_tasks = {}
    return store


class _FakePipeline:
    def __init__(self, redis):
        self._redis = redis
        self._commands = []

    def set(self, key, value):
        self._commands.append(("set", key, value))
        return self

    def zadd(self, key, mapping):
        self._commands.append(("zadd", key, mapping))
        return self

    def delete(self, key):
        self._commands.append(("delete", key))
        return self

    def zrem(self, key, *members):
        self._commands.append(("zrem", key, members))
        return self

    async def execute(self):
        results = []
        for command in self._commands:
            name = command[0]
            if name == "set":
                _, key, value = command
                results.append(await self._redis.set(key, value))
            elif name == "zadd":
                _, key, mapping = command
                results.append(await self._redis.zadd(key, mapping))
            elif name == "delete":
                _, key = command
                results.append(await self._redis.delete(key))
            elif name == "zrem":
                _, key, members = command
                results.append(await self._redis.zrem(key, *members))
        return results


class _FakeRedis:
    def __init__(self):
        self.values = {}
        self.zsets = {}

    def pipeline(self):
        return _FakePipeline(self)

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value):
        self.values[key] = value
        return True

    async def delete(self, key):
        existed = key in self.values
        self.values.pop(key, None)
        return 1 if existed else 0

    async def zadd(self, key, mapping):
        zset = self.zsets.setdefault(key, {})
        zset.update(mapping)
        return len(mapping)

    async def zrem(self, key, *members):
        zset = self.zsets.setdefault(key, {})
        removed = 0
        for member in members:
            if member in zset:
                removed += 1
                zset.pop(member, None)
        return removed

    async def zrevrange(self, key, start, end):
        items = sorted(
            self.zsets.get(key, {}).items(),
            key=lambda item: item[1],
            reverse=True,
        )
        if end == -1:
            selected = items[start:]
        else:
            selected = items[start : end + 1]
        return [member for member, _ in selected]


# ---------------------------------------------------------------------------
# Fixtures for the DB backend
# ---------------------------------------------------------------------------


@pytest.fixture
async def _db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        from api.storage.models import Base

        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_store(_db_engine):
    """TaskStore with use_db=True, wired to an isolated in-memory SQLite DB."""
    from api.storage.tasks import TaskStore

    _AsyncSession = sessionmaker(
        _db_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )

    @asynccontextmanager
    async def _patched_db_context():
        session = _AsyncSession()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    with patch("api.storage.database.get_db_context", _patched_db_context):
        with patch.object(TaskStore, "_init_db"):
            store = TaskStore()
        store.use_db = True
        yield store


# ===========================================================================
# In-memory backend
# ===========================================================================


class TestTaskStoreInMemory:
    """Full CRUD coverage against the dict-backed in-memory store."""

    @pytest.fixture
    def store(self):
        return _make_in_memory_store()

    async def test_get_nonexistent_task_returns_none(self, store):
        result = await store.get_task("does-not-exist")
        assert result is None

    async def test_save_and_get_roundtrip(self, store):
        data = {"task_id": "t1", "status": "pending", "task_type": "dcf"}
        await store.save_task("t1", data)
        task = await store.get_task("t1")
        assert task is not None
        assert task["status"] == "pending"
        assert task["task_type"] == "dcf"

    async def test_save_injects_timestamps(self, store):
        await store.save_task("t2", {"task_id": "t2", "status": "pending"})
        task = await store.get_task("t2")
        assert "created_at" in task
        assert "updated_at" in task

    async def test_save_does_not_overwrite_created_at(self, store):
        original_time = "2026-01-01T00:00:00"
        await store.save_task(
            "t3", {"task_id": "t3", "status": "pending", "created_at": original_time}
        )
        task = await store.get_task("t3")
        assert task["created_at"] == original_time

    async def test_update_task_status(self, store):
        await store.save_task("t4", {"task_id": "t4", "status": "pending"})
        updated = await store.update_task_status("t4", "running")
        assert updated is True
        task = await store.get_task("t4")
        assert task["status"] == "running"

    async def test_update_task_status_with_result(self, store):
        await store.save_task("t5", {"task_id": "t5", "status": "running"})
        result_data = {"answer": 42.0, "valuation": "AAPL"}
        updated = await store.update_task_status("t5", "completed", result=result_data)
        assert updated is True
        task = await store.get_task("t5")
        assert task["status"] == "completed"
        assert task["result"] == result_data

    async def test_update_nonexistent_task_returns_false(self, store):
        updated = await store.update_task_status("ghost-id", "completed")
        assert updated is False

    async def test_delete_existing_task(self, store):
        await store.save_task("t6", {"task_id": "t6", "status": "pending"})
        deleted = await store.delete_task("t6")
        assert deleted is True
        assert await store.get_task("t6") is None

    async def test_delete_nonexistent_task_returns_false(self, store):
        deleted = await store.delete_task("no-such-task")
        assert deleted is False

    async def test_list_tasks_all(self, store):
        for i in range(3):
            await store.save_task(f"list-{i}", {"task_id": f"list-{i}", "status": "pending"})
        tasks = await store.list_tasks()
        ids = [t["task_id"] for t in tasks]
        assert all(f"list-{i}" in ids for i in range(3))

    async def test_list_tasks_filtered_by_status(self, store):
        await store.save_task("running-task", {"task_id": "running-task", "status": "running"})
        await store.save_task("done-task", {"task_id": "done-task", "status": "completed"})
        running = await store.list_tasks(status="running")
        assert len(running) == 1
        assert running[0]["task_id"] == "running-task"

    async def test_list_tasks_respects_limit(self, store):
        for i in range(10):
            await store.save_task(f"bulk-{i}", {"task_id": f"bulk-{i}", "status": "pending"})
        tasks = await store.list_tasks(limit=5)
        assert len(tasks) == 5

    async def test_save_overwrites_existing_task(self, store):
        await store.save_task("t7", {"task_id": "t7", "status": "pending"})
        await store.save_task("t7", {"task_id": "t7", "status": "completed"})
        task = await store.get_task("t7")
        assert task["status"] == "completed"


class TestTaskStoreRedis:
    @pytest.fixture
    def redis_store(self, monkeypatch):
        from api.storage.tasks import TaskStore

        fake_redis = _FakeRedis()

        async def _fake_get_redis(self):
            return fake_redis

        monkeypatch.setattr(TaskStore, "_get_redis", _fake_get_redis)
        return TaskStore(backend="redis", allow_memory_fallback=False)

    async def test_save_get_list_and_delete_use_redis_backend(self, redis_store):
        await redis_store.save_task(
            "redis-1",
            {"task_id": "redis-1", "status": "running", "created_at": "2026-01-01T00:00:00Z"},
        )
        await redis_store.save_task(
            "redis-2",
            {
                "task_id": "redis-2",
                "status": "completed",
                "created_at": "2026-01-02T00:00:00Z",
            },
        )

        task = await redis_store.get_task("redis-1")
        assert task["status"] == "running"

        tasks = await redis_store.list_tasks(limit=2)
        assert [item["task_id"] for item in tasks] == ["redis-2", "redis-1"]

        running = await redis_store.list_tasks(status="running")
        assert [item["task_id"] for item in running] == ["redis-1"]

        assert await redis_store.delete_task("redis-1") is True
        assert await redis_store.get_task("redis-1") is None

    async def test_redis_backend_can_fall_back_to_memory_when_allowed(self, monkeypatch):
        from api.storage.tasks import TaskStore

        async def _redis_unavailable(self):
            raise RuntimeError("redis unavailable")

        monkeypatch.setattr(TaskStore, "_get_redis", _redis_unavailable)
        store = TaskStore(backend="redis", allow_memory_fallback=True)

        await store.save_task("fallback-1", {"task_id": "fallback-1", "status": "pending"})

        task = await store.get_task("fallback-1")
        assert task["status"] == "pending"


# ===========================================================================
# SQLAlchemy database backend
# ===========================================================================


class TestTaskStoreDB:
    """CRUD coverage against a real SQLite in-memory engine."""

    async def test_get_nonexistent_task_returns_none(self, db_store):
        result = await db_store.get_task("no-such-id")
        assert result is None

    async def test_save_and_get_roundtrip(self, db_store):
        data = {
            "task_id": "db-t1",
            "user_id": None,
            "status": "pending",
            "task_type": "dcf_valuation",
            "payload": {"ticker": "AAPL"},
            "result": None,
            "metadata": {},
        }
        await db_store.save_task("db-t1", data)
        task = await db_store.get_task("db-t1")
        assert task is not None
        assert task["task_id"] == "db-t1"
        assert task["status"] == "pending"
        assert task["task_type"] == "dcf_valuation"
        assert task["payload"] == {"ticker": "AAPL"}

    async def test_save_persists_across_store_calls(self, db_store):
        """Saved tasks survive subsequent reads (not just held in memory)."""
        await db_store.save_task("db-t2", {"task_id": "db-t2", "status": "running"})
        # Read a different task first to ensure no caching
        await db_store.get_task("unrelated-id")
        task = await db_store.get_task("db-t2")
        assert task["status"] == "running"

    async def test_save_upserts_existing_task(self, db_store):
        await db_store.save_task("db-t3", {"task_id": "db-t3", "status": "pending"})
        await db_store.save_task(
            "db-t3", {"task_id": "db-t3", "status": "completed", "result": {"val": 1}}
        )
        task = await db_store.get_task("db-t3")
        assert task["status"] == "completed"
        assert task["result"] == {"val": 1}

    async def test_update_task_status(self, db_store):
        await db_store.save_task("db-t4", {"task_id": "db-t4", "status": "pending"})
        ok = await db_store.update_task_status("db-t4", "running")
        assert ok is True
        task = await db_store.get_task("db-t4")
        assert task["status"] == "running"

    async def test_update_task_status_with_result(self, db_store):
        await db_store.save_task("db-t5", {"task_id": "db-t5", "status": "running"})
        ok = await db_store.update_task_status("db-t5", "completed", result={"dcf": 150.0})
        assert ok is True
        task = await db_store.get_task("db-t5")
        assert task["status"] == "completed"
        assert task["result"]["dcf"] == 150.0

    async def test_update_nonexistent_task_returns_false(self, db_store):
        ok = await db_store.update_task_status("ghost", "completed")
        assert ok is False

    async def test_delete_existing_task(self, db_store):
        await db_store.save_task("db-t6", {"task_id": "db-t6", "status": "pending"})
        deleted = await db_store.delete_task("db-t6")
        assert deleted is True
        assert await db_store.get_task("db-t6") is None

    async def test_delete_nonexistent_task_returns_false(self, db_store):
        deleted = await db_store.delete_task("no-such-task")
        assert deleted is False

    async def test_list_tasks_all(self, db_store):
        for i in range(3):
            await db_store.save_task(
                f"db-list-{i}",
                {"task_id": f"db-list-{i}", "status": "pending", "task_type": "batch"},
            )
        tasks = await db_store.list_tasks()
        ids = [t["task_id"] for t in tasks]
        assert all(f"db-list-{i}" in ids for i in range(3))

    async def test_list_tasks_filtered_by_status(self, db_store):
        await db_store.save_task("db-run", {"task_id": "db-run", "status": "running"})
        await db_store.save_task("db-done", {"task_id": "db-done", "status": "completed"})
        running = await db_store.list_tasks(status="running")
        assert len(running) >= 1
        assert all(t["status"] == "running" for t in running)

    async def test_list_tasks_respects_limit(self, db_store):
        for i in range(8):
            await db_store.save_task(
                f"db-bulk-{i}",
                {"task_id": f"db-bulk-{i}", "status": "pending"},
            )
        tasks = await db_store.list_tasks(limit=5)
        assert len(tasks) <= 5

    async def test_returned_dict_has_all_keys(self, db_store):
        await db_store.save_task(
            "db-keys",
            {
                "task_id": "db-keys",
                "status": "pending",
                "payload": {"x": 1},
                "metadata": {},
            },
        )
        task = await db_store.get_task("db-keys")
        for key in (
            "task_id",
            "user_id",
            "status",
            "task_type",
            "payload",
            "result",
            "created_at",
            "updated_at",
            "metadata",
        ):
            assert key in task, f"missing key: {key}"
