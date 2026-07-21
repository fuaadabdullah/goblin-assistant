import importlib
import ssl
import sys
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlencode

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.schema import CreateTable

from api.storage import database
from api.storage.models import UserModel, UserSessionModel

# ---------------------------------------------------------------------------
# Helper: reload api.storage.database with a specific DATABASE_URL
# ---------------------------------------------------------------------------


@contextmanager
def _reload_db_with_url(url: str):
    """Reload api.storage.database with *url* as DATABASE_URL, restore afterwards."""
    mod_name = "api.storage.database"
    old_module = sys.modules.get(mod_name)
    with patch.dict("os.environ", {"DATABASE_URL": url}, clear=False):
        fresh = importlib.import_module(mod_name)
        importlib.reload(fresh)
        try:
            yield fresh
        finally:
            if old_module is not None:
                sys.modules[mod_name] = old_module
            else:
                sys.modules.pop(mod_name, None)


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


# ---------------------------------------------------------------------------
# _build_ssl_context_from_mode
# ---------------------------------------------------------------------------


def test_build_ssl_context_disable_returns_false():
    assert database._build_ssl_context_from_mode("disable") is False
    assert database._build_ssl_context_from_mode("DISABLE") is False


def test_build_ssl_context_verify_ca():
    context = database._build_ssl_context_from_mode("verify-ca")
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is False


def test_build_ssl_context_verify_full():
    context = database._build_ssl_context_from_mode("verify-full")
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_build_ssl_context_default_mode():
    context = database._build_ssl_context_from_mode("require")
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert context.minimum_version == ssl.TLSVersion.TLSv1_2


# ---------------------------------------------------------------------------
# _parse_int_env / _parse_float_env
# ---------------------------------------------------------------------------


def test_parse_int_env_not_set(monkeypatch):
    monkeypatch.delenv("TEST_INT_VAR", raising=False)
    assert database._parse_int_env("TEST_INT_VAR", 42) == 42


def test_parse_int_env_valid(monkeypatch):
    monkeypatch.setenv("TEST_INT_VAR", "7")
    assert database._parse_int_env("TEST_INT_VAR", 42) == 7


def test_parse_int_env_invalid(monkeypatch):
    monkeypatch.setenv("TEST_INT_VAR", "not-a-number")
    assert database._parse_int_env("TEST_INT_VAR", 42) == 42


def test_parse_float_env_not_set(monkeypatch):
    monkeypatch.delenv("TEST_FLOAT_VAR", raising=False)
    assert database._parse_float_env("TEST_FLOAT_VAR", 3.14) == 3.14


def test_parse_float_env_valid(monkeypatch):
    monkeypatch.setenv("TEST_FLOAT_VAR", "2.71")
    assert database._parse_float_env("TEST_FLOAT_VAR", 3.14) == 2.71


def test_parse_float_env_invalid(monkeypatch):
    monkeypatch.setenv("TEST_FLOAT_VAR", "not-a-number")
    assert database._parse_float_env("TEST_FLOAT_VAR", 3.14) == 3.14


# ---------------------------------------------------------------------------
# get_db / get_readonly_db exception paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_db_rollback_on_exception(monkeypatch):
    session = AsyncMock()
    session.close = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: session)

    agen = database.get_db()
    await agen.__anext__()

    with pytest.raises(RuntimeError):
        await agen.athrow(RuntimeError("boom"))

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_readonly_db_rollback_on_exception(monkeypatch):
    session = AsyncMock()
    session.close = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: session)

    agen = database.get_readonly_db()
    await agen.__anext__()

    with pytest.raises(RuntimeError):
        await agen.athrow(RuntimeError("boom"))

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
    session.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# get_db_context / get_readonly_db_context
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_db_context_commits_on_success(monkeypatch):
    session = AsyncMock()
    session.close = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: session)

    async with database.get_db_context() as ctx:
        assert ctx is session

    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_db_context_rollback_on_exception(monkeypatch):
    session = AsyncMock()
    session.close = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: session)

    with pytest.raises(RuntimeError):
        async with database.get_db_context():
            raise RuntimeError("boom")

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_readonly_db_context_no_commit(monkeypatch):
    session = AsyncMock()
    session.close = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: session)

    async with database.get_readonly_db_context() as ctx:
        assert ctx is session

    session.commit.assert_not_awaited()
    session.rollback.assert_not_awaited()
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_readonly_db_context_rollback_on_exception(monkeypatch):
    session = AsyncMock()
    session.close = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: session)

    with pytest.raises(RuntimeError):
        async with database.get_readonly_db_context():
            raise RuntimeError("boom")

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
    session.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# warmup_pool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_warmup_pool_executes_select_one(monkeypatch):
    conn = AsyncMock()
    conn.execute = AsyncMock()

    class FakeConnect:
        async def __aenter__(self):
            return conn

        async def __aexit__(self, *_args):
            return None

    monkeypatch.setattr(database, "engine", SimpleNamespace(connect=FakeConnect))

    await database.warmup_pool()

    conn.execute.assert_awaited_once()
    executed_text = str(conn.execute.await_args[0][0])
    assert "SELECT 1" in executed_text


# ---------------------------------------------------------------------------
# init_db additional branches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_init_db_sqlite_no_vector_extension(monkeypatch):
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
    monkeypatch.setattr(database, "is_postgres", False)

    assert await database.init_db() is True
    assert "CREATE EXTENSION IF NOT EXISTS vector" not in calls
    assert "create_all" in calls


@pytest.mark.asyncio
async def test_init_db_sqlalchemy_error_returns_false(monkeypatch):
    class FailingBegin:
        async def __aenter__(self):
            raise SQLAlchemyError("connection refused")

        async def __aexit__(self, *_args):
            return None

    monkeypatch.setattr(database, "engine", SimpleNamespace(begin=FailingBegin))

    assert await database.init_db() is False


# ---------------------------------------------------------------------------
# Module-level URL normalization and connect_args
# ---------------------------------------------------------------------------


def _normalize_database_url(url: str) -> str:
    """Mirror the module-level normalization logic for isolated unit testing."""
    if url and url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url and url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _build_connect_args(url: str):
    """Mirror the module-level connect_args construction for isolated unit testing."""
    connect_args = {}
    cleaned_url = url
    if url and "postgresql" in url:
        base_url = url
        query_string = ""
        if "?" in url:
            base_url, _, query_string = url.partition("?")
        query_params = parse_qs(query_string, keep_blank_values=True)
        ssl_modes = query_params.pop("sslmode", None)
        if query_params:
            cleaned_url = f"{base_url}?{urlencode(query_params, doseq=True)}"
        else:
            cleaned_url = base_url
        if ssl_modes:
            connect_args["ssl"] = database._build_ssl_context_from_mode(ssl_modes[0])
    return connect_args, cleaned_url


def test_heroku_postgres_url_normalized():
    original_url = "postgres://user:pass@localhost/db"
    expected = "postgresql+asyncpg://user:pass@localhost/db"
    assert _normalize_database_url(original_url) == expected


def test_supabase_postgresql_url_normalized():
    original_url = "postgresql://user:pass@localhost/db"
    expected = "postgresql+asyncpg://user:pass@localhost/db"
    assert _normalize_database_url(original_url) == expected


def test_already_async_url_unchanged():
    url = "postgresql+asyncpg://user:pass@localhost/db"
    assert _normalize_database_url(url) == url


def test_sqlite_url_unchanged():
    url = "sqlite+aiosqlite:///./goblin_assistant.db"
    assert _normalize_database_url(url) == url


def test_build_connect_args_extracts_sslmode():
    url = "postgresql+asyncpg://user:pass@localhost/db?sslmode=disable"
    connect_args, cleaned_url = _build_connect_args(url)
    assert connect_args["ssl"] is False
    assert "sslmode" not in cleaned_url


def test_build_connect_args_preserves_other_query_params():
    url = "postgresql+asyncpg://user:pass@localhost/db?foo=bar&baz=qux"
    connect_args, cleaned_url = _build_connect_args(url)
    assert connect_args == {}
    assert "foo=bar" in cleaned_url
    assert "baz=qux" in cleaned_url


# ---------------------------------------------------------------------------
# Reload-based tests — exercise module-level branches (lines 29, 39, 87-98,
# 102, 115) that only fire when DATABASE_URL is set to a specific value
# before import.
# ---------------------------------------------------------------------------


def test_heroku_postgres_url_normalized_at_module_level():
    """Line 29: postgres:// → postgresql+asyncpg:// rewrite fires at import."""
    with _reload_db_with_url("postgres://user:pass@db.example.com/mydb") as m:
        assert m.DATABASE_URL.startswith("postgresql+asyncpg://")
        assert "postgres://" not in m.DATABASE_URL


def test_supabase_postgresql_url_normalized_at_module_level():
    """Line 39: postgresql:// (non-asyncpg) → postgresql+asyncpg:// fires at import."""
    with _reload_db_with_url("postgresql://user:pass@db.example.com/mydb") as m:
        assert m.DATABASE_URL.startswith("postgresql+asyncpg://")


def test_sslmode_stripped_from_url_and_ssl_context_built():
    """Lines 87-98 (True path): sslmode is extracted, ssl context wired into connect_args."""
    url = "postgresql+asyncpg://user:pass@db.example.com/mydb?sslmode=disable"
    with _reload_db_with_url(url) as m:
        assert "sslmode" not in m.DATABASE_URL
        assert m.connect_args.get("ssl") is False


def test_sslmode_stripped_non_empty_remaining_params():
    """Lines 93-94 (True branch): extra query params kept after sslmode is popped."""
    url = "postgresql+asyncpg://user:pass@db.example.com/mydb?sslmode=disable&connect_timeout=10"
    with _reload_db_with_url(url) as m:
        assert "sslmode" not in m.DATABASE_URL
        assert "connect_timeout=10" in m.DATABASE_URL


def test_no_sslmode_no_question_mark_url_unchanged():
    """Lines 87-96 (False ssl branch): plain postgresql URL has no sslmode to strip."""
    url = "postgresql+asyncpg://user:pass@db.example.com/mydb"
    with _reload_db_with_url(url) as m:
        assert url == m.DATABASE_URL
        assert "ssl" not in m.connect_args


def test_password_in_url_triggers_warning_branch(capsys):
    """Line 102: URL containing 'password' causes structlog warning (written to stdout)."""
    url = "postgresql+asyncpg://admin:password@db.example.com/mydb"
    with _reload_db_with_url(url) as m:
        # Verify the warning branch was reached — structlog writes JSON to stdout.
        out = capsys.readouterr().out
        assert "password" in out
        assert m.is_postgres is True


def test_postgres_engine_uses_pool_kwargs():
    """Line 115: is_postgres=True → AsyncAdaptedQueuePool kwargs applied to engine."""
    from sqlalchemy.pool import AsyncAdaptedQueuePool

    url = "postgresql+asyncpg://user:pass@db.example.com/mydb"
    with _reload_db_with_url(url) as m:
        assert m.is_postgres is True
        assert isinstance(m.engine.pool, AsyncAdaptedQueuePool)
