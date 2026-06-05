from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from api.storage import database
from api.storage.models import UserModel, UserSessionModel


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


def test_boolean_server_defaults_compile_for_postgres():
    dialect = postgresql.dialect()

    users_ddl = str(CreateTable(UserModel.__table__).compile(dialect=dialect))
    sessions_ddl = str(CreateTable(UserSessionModel.__table__).compile(dialect=dialect))

    assert "is_active BOOLEAN DEFAULT true NOT NULL" in users_ddl
    assert "is_revoked BOOLEAN DEFAULT false NOT NULL" in sessions_ddl


@pytest.mark.asyncio
async def test_init_db_enables_vector_extension_before_creating_postgres_tables(
    monkeypatch,
):
    calls = []

    class FakeConnection:
        async def execute(self, statement):
            calls.append(str(statement))

        async def run_sync(self, _operation):
            calls.append("create_all")

    class FakeBegin:
        async def __aenter__(self):
            return FakeConnection()

        async def __aexit__(self, *_args):
            return None

    monkeypatch.setattr(database, "engine", SimpleNamespace(begin=FakeBegin))
    monkeypatch.setattr(database, "is_postgres", True)

    assert await database.init_db() is True
    assert calls == ["CREATE EXTENSION IF NOT EXISTS vector", "create_all"]
