"""Database connection pool benchmarks.

Measures pool acquisition latency, concurrent connection handling,
and read-only vs read-write session overhead.

Run with:
    pytest apps/api/src/api/tests/test_db_pool.py -v --benchmark-enable
"""

from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _acquire_and_release_readonly() -> None:
    """Simulate a read-only endpoint: acquire session, SELECT, release."""
    from api.storage.database import get_readonly_db

    gen = get_readonly_db()
    session: AsyncSession = await gen.__anext__()
    try:
        await session.execute(text("SELECT 1"))
    finally:
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass


async def _acquire_and_release_readwrite() -> None:
    """Simulate a read-write endpoint: acquire session, SELECT, commit, release."""
    from api.storage.database import get_db

    gen = get_db()
    session: AsyncSession = await gen.__anext__()
    try:
        await session.execute(text("SELECT 1"))
    finally:
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass


async def _concurrent_acquisitions(n: int, readonly: bool) -> None:
    """Acquire n sessions concurrently and release them."""
    fn = _acquire_and_release_readonly if readonly else _acquire_and_release_readwrite
    await asyncio.gather(*[fn() for _ in range(n)])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_engine():
    """Return the global engine for pool stats inspection."""
    from api.storage.database import engine

    return engine


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_readonly_session_no_commit(benchmark):
    """Read-only session should NOT issue a COMMIT."""
    await benchmark.pedantic(
        _acquire_and_release_readonly,
        rounds=50,
        warmup_rounds=5,
    )


@pytest.mark.asyncio
async def test_readwrite_session_commits(benchmark):
    """Read-write session issues a COMMIT (baseline comparison)."""
    await benchmark.pedantic(
        _acquire_and_release_readwrite,
        rounds=50,
        warmup_rounds=5,
    )


@pytest.mark.asyncio
async def test_concurrent_pool_5(benchmark):
    """5 concurrent sessions should not contend on the pool."""
    await benchmark.pedantic(
        _concurrent_acquisitions,
        args=(5, True),
        rounds=20,
        warmup_rounds=3,
    )


@pytest.mark.asyncio
async def test_concurrent_pool_10(benchmark):
    """10 concurrent sessions (pool_size + overflow)."""
    await benchmark.pedantic(
        _concurrent_acquisitions,
        args=(10, True),
        rounds=20,
        warmup_rounds=3,
    )


@pytest.mark.asyncio
async def test_concurrent_pool_15(benchmark):
    """15 concurrent sessions (exceeds default pool_size=5, needs overflow)."""
    await benchmark.pedantic(
        _concurrent_acquisitions,
        args=(15, True),
        rounds=10,
        warmup_rounds=2,
    )


def test_pool_config_values():
    """Verify pool tuning knobs are applied correctly."""
    from api.storage.database import engine, is_postgres

    if not is_postgres:
        pytest.skip("Pool tuning only applies to PostgreSQL")

    pool = engine.pool
    assert pool.size() == int(os.getenv("DATABASE_POOL_SIZE", "5"))
    assert pool.overflow() == int(os.getenv("DATABASE_MAX_OVERFLOW", "10"))


def test_pool_recycle_configured():
    """pool_recycle should be set to prevent stale connections."""
    from api.storage.database import engine, is_postgres

    if not is_postgres:
        pytest.skip("Pool recycle only applies to PostgreSQL")

    pool = engine.pool
    assert pool._recycle == int(os.getenv("DATABASE_POOL_RECYCLE", "3600"))
