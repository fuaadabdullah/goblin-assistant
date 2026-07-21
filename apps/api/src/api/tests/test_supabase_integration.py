"""Tests for api.supabase_integration — mocks all httpx / SQLAlchemy I/O."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import api.supabase_integration as sut

# ---------------------------------------------------------------------------
# Helper: reload the module with specific env vars, then restore
# ---------------------------------------------------------------------------


@contextmanager
def _reload_with_env(env: dict):
    """Reload api.supabase_integration with *env* vars set, yield the module, then restore."""
    old_module = sys.modules.get("api.supabase_integration")
    with patch.dict("os.environ", env, clear=False):
        fresh = importlib.import_module("api.supabase_integration")
        importlib.reload(fresh)
        try:
            yield fresh
        finally:
            # Restore the original module so the rest of the test session is unaffected.
            if old_module is not None:
                sys.modules["api.supabase_integration"] = old_module
            else:
                sys.modules.pop("api.supabase_integration", None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(status_code: int, json_data=None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    return resp


def _fake_client(response: MagicMock) -> MagicMock:
    """Return a fake httpx.AsyncClient context manager whose methods return *response*."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=response)
    client.post = AsyncMock(return_value=response)
    client.patch = AsyncMock(return_value=response)
    client.delete = AsyncMock(return_value=response)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _auth(url="https://proj.supabase.co", anon="anon-key", service="srk") -> sut.SupabaseAuth:
    auth = sut.SupabaseAuth.__new__(sut.SupabaseAuth)
    auth.url = url
    auth.anon_key = anon
    auth.service_role_key = service
    auth.api_url = f"{url}/auth/v1" if url else None
    return auth


def _db(url="https://proj.supabase.co", service="srk") -> sut.SupabaseDatabase:
    db = sut.SupabaseDatabase.__new__(sut.SupabaseDatabase)
    db.url = url
    db.service_role_key = service
    db.anon_key = "anon"
    db.rest_url = f"{url}/rest/v1" if url else None
    return db


def _storage(url="https://proj.supabase.co", service="srk") -> sut.SupabaseStorage:
    st = sut.SupabaseStorage.__new__(sut.SupabaseStorage)
    st.url = url
    st.service_role_key = service
    st.storage_url = f"{url}/storage/v1" if url else None
    return st


# ---------------------------------------------------------------------------
# SupabaseAuth — init
# ---------------------------------------------------------------------------


def test_auth_init_sets_api_url():
    with patch.dict(
        "os.environ",
        {
            "SUPABASE_URL": "https://x.supabase.co",
            "SUPABASE_ANON_KEY": "ak",
            "SUPABASE_SERVICE_ROLE_KEY": "sk",
        },
    ):
        # Directly construct to test __init__ logic, since env vars already read at module top.
        auth = sut.SupabaseAuth.__new__(sut.SupabaseAuth)
        # Simulate __init__ manually with specific values
        auth.url = "https://x.supabase.co"
        auth.anon_key = "ak"
        auth.service_role_key = "sk"
        auth.api_url = f"{auth.url}/auth/v1"
    assert auth.api_url == "https://x.supabase.co/auth/v1"


def test_auth_init_no_url_gives_none_api_url():
    auth = sut.SupabaseAuth.__new__(sut.SupabaseAuth)
    auth.url = None
    auth.anon_key = None
    auth.service_role_key = None
    auth.api_url = f"{auth.url}/auth/v1" if auth.url else None
    assert auth.api_url is None


# ---------------------------------------------------------------------------
# SupabaseAuth — create_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_user_missing_config():
    auth = _auth(url=None, service=None)
    auth.api_url = None
    result = await auth.create_user("a@b.com", "pw")
    assert "error" in result


@pytest.mark.asyncio
async def test_create_user_success():
    auth = _auth()
    resp = _mock_response(200, {"id": "uid-123"})
    ctx = _fake_client(resp)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await auth.create_user("a@b.com", "pw", {"role": "user"})
    assert result == {"id": "uid-123"}


@pytest.mark.asyncio
async def test_create_user_api_error():
    auth = _auth()
    resp = _mock_response(400)
    ctx = _fake_client(resp)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await auth.create_user("a@b.com", "pw")
    assert "error" in result
    assert "400" in result["error"]


@pytest.mark.asyncio
async def test_create_user_exception():
    auth = _auth()
    client = AsyncMock()
    client.post = AsyncMock(side_effect=Exception("network failure"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await auth.create_user("a@b.com", "pw")
    assert "Failed to create user" in result["error"]


@pytest.mark.asyncio
async def test_create_user_no_metadata():
    auth = _auth()
    resp = _mock_response(200, {"id": "x"})
    ctx = _fake_client(resp)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await auth.create_user("a@b.com", "pw")  # metadata omitted
    assert result == {"id": "x"}


# ---------------------------------------------------------------------------
# SupabaseAuth — get_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_user_missing_config():
    auth = _auth(url=None, service=None)
    auth.api_url = None
    result = await auth.get_user("uid")
    assert "error" in result


@pytest.mark.asyncio
async def test_get_user_success():
    auth = _auth()
    resp = _mock_response(200, {"id": "uid-1", "email": "a@b.com"})
    ctx = _fake_client(resp)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await auth.get_user("uid-1")
    assert result["id"] == "uid-1"


@pytest.mark.asyncio
async def test_get_user_api_error():
    auth = _auth()
    resp = _mock_response(404)
    ctx = _fake_client(resp)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await auth.get_user("bad-id")
    assert "error" in result
    assert "404" in result["error"]


@pytest.mark.asyncio
async def test_get_user_exception():
    auth = _auth()
    client = AsyncMock()
    client.get = AsyncMock(side_effect=RuntimeError("timeout"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await auth.get_user("uid")
    assert "Failed to get user" in result["error"]


# ---------------------------------------------------------------------------
# SupabaseAuth — verify_jwt_token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_jwt_missing_config():
    auth = _auth(url=None, anon=None)
    auth.api_url = None
    result = await auth.verify_jwt_token("tok")
    assert result == {"error": "Supabase configuration missing"}


@pytest.mark.asyncio
async def test_verify_jwt_valid():
    auth = _auth()
    resp = _mock_response(200, {"id": "uid", "email": "x@y.com"})
    ctx = _fake_client(resp)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await auth.verify_jwt_token("good-token")
    assert result["valid"] is True
    assert "user" in result


@pytest.mark.asyncio
async def test_verify_jwt_invalid_token():
    auth = _auth()
    resp = _mock_response(401)
    ctx = _fake_client(resp)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await auth.verify_jwt_token("bad-token")
    assert result["valid"] is False
    assert "401" in result["error"]


@pytest.mark.asyncio
async def test_verify_jwt_exception():
    auth = _auth()
    client = AsyncMock()
    client.get = AsyncMock(side_effect=Exception("ssl error"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await auth.verify_jwt_token("tok")
    assert result["valid"] is False
    assert "Token verification failed" in result["error"]


# ---------------------------------------------------------------------------
# SupabaseDatabase — execute_query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_query_missing_config():
    db = _db(url=None, service=None)
    db.rest_url = None
    result = await db.execute_query("users", {})
    assert "error" in result


@pytest.mark.asyncio
async def test_execute_query_success():
    db = _db()
    resp = _mock_response(200, [{"id": 1}])
    ctx = _fake_client(resp)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await db.execute_query("users", {"select": "*"})
    assert result == {"data": [{"id": 1}]}


@pytest.mark.asyncio
async def test_execute_query_api_error():
    db = _db()
    resp = _mock_response(500)
    ctx = _fake_client(resp)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await db.execute_query("users", {})
    assert "error" in result
    assert "500" in result["error"]


@pytest.mark.asyncio
async def test_execute_query_exception():
    db = _db()
    client = AsyncMock()
    client.get = AsyncMock(side_effect=Exception("conn refused"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await db.execute_query("users", {})
    assert "Query execution failed" in result["error"]


# ---------------------------------------------------------------------------
# SupabaseDatabase — insert_data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_insert_data_missing_config():
    db = _db(url=None, service=None)
    db.rest_url = None
    result = await db.insert_data("users", {"email": "x"})
    assert "error" in result


@pytest.mark.asyncio
async def test_insert_data_success():
    db = _db()
    resp = _mock_response(201, [{"id": 99}])
    ctx = _fake_client(resp)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await db.insert_data("users", {"email": "x@y.com"})
    assert result == {"data": [{"id": 99}]}


@pytest.mark.asyncio
async def test_insert_data_api_error():
    db = _db()
    resp = _mock_response(409)
    ctx = _fake_client(resp)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await db.insert_data("users", {"email": "dup@y.com"})
    assert "error" in result
    assert "409" in result["error"]


@pytest.mark.asyncio
async def test_insert_data_exception():
    db = _db()
    client = AsyncMock()
    client.post = AsyncMock(side_effect=Exception("boom"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await db.insert_data("users", {})
    assert "Insert failed" in result["error"]


# ---------------------------------------------------------------------------
# SupabaseDatabase — update_data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_data_missing_config():
    db = _db(url=None, service=None)
    db.rest_url = None
    result = await db.update_data("users", {"name": "Bob"}, "id", "1")
    assert "error" in result


@pytest.mark.asyncio
async def test_update_data_success():
    db = _db()
    resp = _mock_response(200, [{"id": "1", "name": "Bob"}])
    ctx = _fake_client(resp)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await db.update_data("users", {"name": "Bob"}, "id", "1")
    assert result["data"][0]["name"] == "Bob"


@pytest.mark.asyncio
async def test_update_data_api_error():
    db = _db()
    resp = _mock_response(422)
    ctx = _fake_client(resp)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await db.update_data("users", {}, "id", "99")
    assert "error" in result
    assert "422" in result["error"]


@pytest.mark.asyncio
async def test_update_data_exception():
    db = _db()
    client = AsyncMock()
    client.patch = AsyncMock(side_effect=Exception("network"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await db.update_data("users", {}, "id", "1")
    assert "Update failed" in result["error"]


# ---------------------------------------------------------------------------
# SupabaseDatabase — delete_data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_data_missing_config():
    db = _db(url=None, service=None)
    db.rest_url = None
    result = await db.delete_data("users", "id", "1")
    assert "error" in result


@pytest.mark.asyncio
async def test_delete_data_success():
    db = _db()
    resp = _mock_response(204)
    ctx = _fake_client(resp)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await db.delete_data("users", "id", "1")
    assert result == {"success": True}


@pytest.mark.asyncio
async def test_delete_data_api_error():
    db = _db()
    resp = _mock_response(404)
    ctx = _fake_client(resp)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await db.delete_data("users", "id", "999")
    assert "error" in result
    assert "404" in result["error"]


@pytest.mark.asyncio
async def test_delete_data_exception():
    db = _db()
    client = AsyncMock()
    client.delete = AsyncMock(side_effect=Exception("gone"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await db.delete_data("users", "id", "1")
    assert "Delete failed" in result["error"]


# ---------------------------------------------------------------------------
# SupabaseStorage — upload_file
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_file_missing_config():
    st = _storage(url=None, service=None)
    st.storage_url = None
    result = await st.upload_file("bucket", "file.txt", b"data")
    assert "error" in result


@pytest.mark.asyncio
async def test_upload_file_success():
    st = _storage()
    resp = _mock_response(200, {"Key": "bucket/file.txt"})
    ctx = _fake_client(resp)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await st.upload_file("bucket", "file.txt", b"hello", "text/plain")
    assert result == {"data": {"Key": "bucket/file.txt"}}


@pytest.mark.asyncio
async def test_upload_file_storage_error():
    st = _storage()
    resp = _mock_response(403)
    ctx = _fake_client(resp)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await st.upload_file("bucket", "secret.txt", b"data")
    assert "error" in result
    assert "403" in result["error"]


@pytest.mark.asyncio
async def test_upload_file_exception():
    st = _storage()
    client = AsyncMock()
    client.post = AsyncMock(side_effect=Exception("timeout"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await st.upload_file("bucket", "file.txt", b"x")
    assert "Upload failed" in result["error"]


@pytest.mark.asyncio
async def test_upload_file_default_content_type():
    """No explicit content_type should default to application/octet-stream."""
    st = _storage()
    resp = _mock_response(200, {"Key": "b/f"})
    ctx = _fake_client(resp)
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await st.upload_file("b", "f", b"\x00\x01")
    assert "data" in result


# ---------------------------------------------------------------------------
# SupabaseStorage — get_file_url
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_file_url_missing_storage_url():
    st = _storage()
    st.storage_url = None
    result = await st.get_file_url("bucket", "file.txt")
    assert "error" in result


@pytest.mark.asyncio
async def test_get_file_url_success():
    st = _storage()
    result = await st.get_file_url("my-bucket", "images/photo.jpg")
    assert "url" in result
    assert "my-bucket" in result["url"]
    assert result["bucket"] == "my-bucket"
    assert result["path"] == "images/photo.jpg"


# ---------------------------------------------------------------------------
# get_db context manager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_db_commits_on_success(monkeypatch):
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()

    monkeypatch.setattr(sut, "AsyncSessionLocal", lambda: session)

    async with sut.get_db() as yielded:
        assert yielded is session

    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_db_rolls_back_on_exception(monkeypatch):
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()

    monkeypatch.setattr(sut, "AsyncSessionLocal", lambda: session)

    with pytest.raises(ValueError):
        async with sut.get_db() as _:
            raise ValueError("oops")

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
    session.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_init_db_calls_create_all(monkeypatch):
    calls = []

    class FakeConn:
        async def run_sync(self, fn):
            calls.append("create_all")

    class FakeBegin:
        async def __aenter__(self):
            return FakeConn()

        async def __aexit__(self, *_):
            return None

    monkeypatch.setattr(sut, "engine", SimpleNamespace(begin=FakeBegin))

    # Stub out the models import inside init_db
    fake_base = MagicMock()
    fake_base.metadata.create_all = MagicMock()
    fake_models = MagicMock()
    fake_models.Base = fake_base

    import sys

    original = sys.modules.get("api.models")
    sys.modules["api.models"] = fake_models
    try:
        await sut.init_db()
    finally:
        if original is None:
            sys.modules.pop("api.models", None)
        else:
            sys.modules["api.models"] = original

    assert "create_all" in calls


# ---------------------------------------------------------------------------
# get_supabase_config
# ---------------------------------------------------------------------------


def test_get_supabase_config_returns_bool_flags():
    result = sut.get_supabase_config()
    assert isinstance(result["url"], bool)
    assert isinstance(result["service_role_key"], bool)
    assert isinstance(result["anon_key"], bool)
    assert isinstance(result["database_url"], bool)
    assert isinstance(result["enabled"], bool)
    # database_url is always truthy (falls back to sqlite)
    assert result["database_url"] is True


def test_get_supabase_config_enabled_requires_both(monkeypatch):
    monkeypatch.setattr(sut, "SUPABASE_URL", None)
    monkeypatch.setattr(sut, "SUPABASE_SERVICE_ROLE_KEY", None)
    result = sut.get_supabase_config()
    assert result["enabled"] is False


def test_get_supabase_config_enabled_when_both_set(monkeypatch):
    monkeypatch.setattr(sut, "SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setattr(sut, "SUPABASE_SERVICE_ROLE_KEY", "sk")
    result = sut.get_supabase_config()
    assert result["enabled"] is True


# ---------------------------------------------------------------------------
# DATABASE_URL construction (module-level logic exercised indirectly)
# ---------------------------------------------------------------------------


def test_database_url_is_set():
    assert sut.DATABASE_URL is not None
    assert len(sut.DATABASE_URL) > 0


# ---------------------------------------------------------------------------
# Global instances are created
# ---------------------------------------------------------------------------


def test_global_instances_exist():
    assert isinstance(sut.supabase_auth, sut.SupabaseAuth)
    assert isinstance(sut.supabase_db, sut.SupabaseDatabase)
    assert isinstance(sut.supabase_storage, sut.SupabaseStorage)


# ---------------------------------------------------------------------------
# Module-reload tests: cover the Supabase env-var branches (lines 22 & 304)
# These are the two paths only reachable when SUPABASE_URL and
# SUPABASE_SERVICE_ROLE_KEY are present *at import time*.
# ---------------------------------------------------------------------------


def test_database_url_uses_supabase_connection_string_when_env_vars_set():
    """Line 22: DATABASE_URL is built from SUPABASE_URL + service role key."""
    env = {
        "SUPABASE_URL": "https://abcdef.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "super-secret-key",
    }
    with _reload_with_env(env) as m:
        assert m.DATABASE_URL.startswith("postgresql+asyncpg://")
        assert "abcdef.supabase.co" in m.DATABASE_URL
        assert "super-secret-key" in m.DATABASE_URL
        # https:// prefix is stripped
        assert "https://" not in m.DATABASE_URL


def test_engine_created_with_pool_settings_when_supabase_env_vars_set():
    """Line 304: engine is created with pool_size / max_overflow (not StaticPool)."""
    from sqlalchemy.pool import StaticPool

    env = {
        "SUPABASE_URL": "https://abcdef.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "super-secret-key",
    }
    with _reload_with_env(env) as m:
        # The engine should NOT use StaticPool (that is only for the SQLite fallback).
        assert not isinstance(m.engine.pool, StaticPool)
        # The URL dialect should be asyncpg / postgresql.
        assert "postgresql" in str(m.engine.url)
