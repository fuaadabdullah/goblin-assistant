from unittest.mock import AsyncMock

import pytest

from api.storage import database


@pytest.mark.asyncio
async def test_get_readonly_db_does_not_commit(monkeypatch):
    session = AsyncMock()
    session.close = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: session)

    agen = database.get_readonly_db()
    yielded = await agen.__anext__()

    assert yielded is session

    await agen.aclose()

    session.commit.assert_not_awaited()
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_db_commits_on_exit(monkeypatch):
    session = AsyncMock()
    session.close = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: session)

    agen = database.get_db()
    yielded = await agen.__anext__()

    assert yielded is session

    with pytest.raises(StopAsyncIteration):
        await agen.__anext__()

    session.commit.assert_awaited_once()
    session.close.assert_awaited_once()
