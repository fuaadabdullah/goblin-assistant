"""Tests for usage event persistence and per-day aggregation."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


def _make_in_memory_store():
    from api.storage.usage_events import UsageEventStore

    store = UsageEventStore.__new__(UsageEventStore)
    store.use_db = False
    store._in_memory_events = []
    store._in_memory_daily = {}
    return store


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
    from api.storage.usage_events import UsageEventStore

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
        store = UsageEventStore.__new__(UsageEventStore)
        store.use_db = True
        store._in_memory_events = []
        store._in_memory_daily = {}
        yield store


class TestUsageEventStoreInMemory:
    async def test_save_event_updates_daily_aggregate(self):
        store = _make_in_memory_store()

        await store.save_event(
            {
                "user_id": "u1",
                "conversation_id": "c1",
                "message_id": "m1",
                "provider": "openai",
                "model": "gpt-4o-mini",
                "prompt_tokens": 120,
                "completion_tokens": 30,
                "total_tokens": 150,
                "cost_usd": 0.002,
            }
        )

        usage = await store.get_daily_usage("u1")
        assert usage["event_count"] == 1
        assert usage["prompt_tokens"] == 120
        assert usage["completion_tokens"] == 30
        assert usage["total_tokens"] == 150
        assert usage["total_cost_usd"] == pytest.approx(0.002)

    async def test_check_limits_uses_daily_aggregate(self, monkeypatch):
        store = _make_in_memory_store()
        monkeypatch.setenv("GOBLIN_DAILY_TOKEN_LIMIT", "100")

        await store.save_event(
            {
                "user_id": "u1",
                "total_tokens": 90,
                "cost_usd": 0.0,
            }
        )

        allowed = await store.check_limits("u1", additional_tokens=5)
        blocked = await store.check_limits("u1", additional_tokens=11)

        assert allowed["allowed"] is True
        assert blocked["allowed"] is False
        assert blocked["reason"] == "daily_token_limit_exceeded"


class TestUsageEventStoreDB:
    async def test_save_event_persists_daily_aggregate(self, db_store):
        await db_store.save_event(
            {
                "user_id": "db-user",
                "conversation_id": "conv-1",
                "message_id": "msg-1",
                "provider": "openai",
                "model": "gpt-4o-mini",
                "prompt_tokens": 50,
                "completion_tokens": 20,
                "cost_usd": 0.001,
            }
        )

        usage = await db_store.get_daily_usage("db-user", usage_date=date.today())
        assert usage["event_count"] == 1
        assert usage["total_tokens"] == 70
        assert usage["prompt_tokens"] == 50
        assert usage["completion_tokens"] == 20
        assert usage["total_cost_usd"] == pytest.approx(0.001)
