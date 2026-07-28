"""Tests for usage event persistence and per-day aggregation."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
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
                "request_id": "req-1",
                "route": "/api/v1/chat/stream",
                "conversation_id": "c1",
                "message_id": "m1",
                "provider": "openai",
                "model": "gpt-4o-mini",
                "prompt_tokens": 120,
                "completion_tokens": 30,
                "total_tokens": 150,
                "cost_usd": 0.002,
                "latency_ms": 123.4,
                "status_code": 200,
            }
        )

        usage = await store.get_daily_usage("u1")
        assert usage["event_count"] == 1
        assert usage["prompt_tokens"] == 120
        assert usage["completion_tokens"] == 30
        assert usage["total_tokens"] == 150
        assert usage["total_cost_usd"] == pytest.approx(0.002)

        rollup = await store.get_model_rollup(provider="openai", model="gpt-4o-mini")
        assert rollup[0]["request_count"] == 1
        assert rollup[0]["total_latency_ms"] == pytest.approx(123.4)

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


class TestUsageEventStoreInMemoryCostLimit:
    async def test_check_limits_blocks_on_daily_cost_cap(self, monkeypatch):
        store = _make_in_memory_store()
        monkeypatch.setenv("GOBLIN_DAILY_COST_LIMIT_USD", "0.01")

        await store.save_event({"user_id": "u2", "total_tokens": 0, "cost_usd": 0.008})

        allowed = await store.check_limits("u2", additional_cost_usd=0.001)
        blocked = await store.check_limits("u2", additional_cost_usd=0.003)

        assert allowed["allowed"] is True
        assert blocked["allowed"] is False
        assert blocked["reason"] == "daily_cost_limit_exceeded"

    async def test_check_limits_allows_when_no_limits_configured(self, monkeypatch):
        store = _make_in_memory_store()
        monkeypatch.delenv("GOBLIN_DAILY_TOKEN_LIMIT", raising=False)
        monkeypatch.delenv("GOBLIN_DAILY_COST_LIMIT_USD", raising=False)

        await store.save_event({"user_id": "u3", "total_tokens": 999_999, "cost_usd": 999.0})

        result = await store.check_limits("u3", additional_tokens=50_000, additional_cost_usd=50.0)

        assert result["allowed"] is True
        assert result["reason"] is None

    async def test_get_total_spend_for_date_sums_all_users(self):
        store = _make_in_memory_store()
        today = datetime.utcnow().date()

        await store.save_event({"user_id": "a", "cost_usd": 0.05})
        await store.save_event({"user_id": "b", "cost_usd": 0.03})
        await store.save_event({"user_id": "a", "cost_usd": 0.02})

        total = await store.get_total_spend_for_date(today)

        assert total == pytest.approx(0.10)

    async def test_get_total_spend_for_date_excludes_other_dates(self):
        from datetime import timedelta

        store = _make_in_memory_store()
        yesterday = datetime.utcnow().date() - timedelta(days=1)

        await store.save_event({"user_id": "u", "cost_usd": 0.99})

        total = await store.get_total_spend_for_date(yesterday)

        assert total == pytest.approx(0.0)

    async def test_daily_usage_accumulates_multiple_events(self):
        store = _make_in_memory_store()

        for i in range(5):
            await store.save_event(
                {
                    "user_id": "u4",
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                    "cost_usd": 0.001,
                }
            )

        usage = await store.get_daily_usage("u4")
        assert usage["event_count"] == 5
        assert usage["total_tokens"] == 75
        assert usage["total_cost_usd"] == pytest.approx(0.005)


class TestUsageEventStoreDB:
    async def test_save_event_persists_daily_aggregate(self, db_store):
        await db_store.save_event(
            {
                "user_id": "db-user",
                "request_id": "req-2",
                "conversation_id": "conv-1",
                "message_id": "msg-1",
                "provider": "openai",
                "model": "gpt-4o-mini",
                "prompt_tokens": 50,
                "completion_tokens": 20,
                "cost_usd": 0.001,
                "latency_ms": 42.0,
            }
        )

        usage = await db_store.get_daily_usage("db-user", usage_date=datetime.utcnow().date())
        assert usage["event_count"] == 1
        assert usage["total_tokens"] == 70
        assert usage["prompt_tokens"] == 50
        assert usage["completion_tokens"] == 20
        assert usage["total_cost_usd"] == pytest.approx(0.001)

        rollup = await db_store.get_model_rollup(provider="openai", model="gpt-4o-mini")
        assert rollup[0]["request_count"] == 1
        assert rollup[0]["total_latency_ms"] == pytest.approx(42.0)
