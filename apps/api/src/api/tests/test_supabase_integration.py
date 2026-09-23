"""Tests for api.supabase_integration — the Supabase Admin API wrapper.

SupabaseAuth, SupabaseDatabase and SupabaseStorage all follow the same
shape: bail out with a config-missing sentinel when unconfigured, build
service-role headers, make one httpx call, and translate the status code.
Each method gets an unconfigured case, a success case, a non-2xx case, and
a network-exception case.

Configuration is read once at import time into module-level globals, so the
classes are instantiated fresh per test with those attributes patched
directly rather than re-importing the module for every case.
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.supabase_integration import (
    SupabaseAuth,
    SupabaseDatabase,
    SupabaseStorage,
    get_supabase_config,
)


def _auth(*, configured: bool = True) -> SupabaseAuth:
    instance = SupabaseAuth()
    if configured:
        instance.url = "https://proj.supabase.co"
        instance.anon_key = "anon-key"
        instance.service_role_key = "service-key"
        instance.api_url = "https://proj.supabase.co/auth/v1"
    else:
        instance.url = None
        instance.anon_key = None
        instance.service_role_key = None
        instance.api_url = None
    return instance


def _db(*, configured: bool = True) -> SupabaseDatabase:
    instance = SupabaseDatabase()
    if configured:
        instance.url = "https://proj.supabase.co"
        instance.service_role_key = "service-key"
        instance.anon_key = "anon-key"
        instance.rest_url = "https://proj.supabase.co/rest/v1"
    else:
        instance.url = None
        instance.service_role_key = None
        instance.rest_url = None
    return instance


def _storage(*, configured: bool = True) -> SupabaseStorage:
    instance = SupabaseStorage()
    if configured:
        instance.url = "https://proj.supabase.co"
        instance.service_role_key = "service-key"
        instance.storage_url = "https://proj.supabase.co/storage/v1"
    else:
        instance.url = None
        instance.service_role_key = None
        instance.storage_url = None
    return instance


def _fake_client(response: Any = None, *, raises: Exception | None = None) -> MagicMock:
    client = MagicMock()
    for method in ("get", "post", "patch", "delete"):
        mock = AsyncMock(side_effect=raises) if raises else AsyncMock(return_value=response)
        setattr(client, method, mock)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


class _Resp:
    def __init__(self, status_code: int, payload: Any = None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


def _patched(client: MagicMock):
    return patch("api.supabase_integration.httpx.AsyncClient", return_value=client)


# ---------------------------------------------------------------------------
# SupabaseAuth
# ---------------------------------------------------------------------------


class TestCreateUser:
    @pytest.mark.asyncio
    async def test_reports_missing_configuration(self):
        result = await _auth(configured=False).create_user("a@example.com", "pw")

        assert result == {"error": "Supabase configuration missing"}

    @pytest.mark.asyncio
    async def test_returns_the_created_user_on_success(self):
        client = _fake_client(_Resp(200, {"id": "u-1"}))

        with _patched(client):
            result = await _auth().create_user("a@example.com", "pw", {"role": "member"})

        assert result == {"id": "u-1"}
        assert client.post.await_args.kwargs["json"]["user_metadata"] == {"role": "member"}

    @pytest.mark.asyncio
    async def test_defaults_metadata_to_empty(self):
        client = _fake_client(_Resp(200, {}))

        with _patched(client):
            await _auth().create_user("a@example.com", "pw")

        assert client.post.await_args.kwargs["json"]["user_metadata"] == {}

    @pytest.mark.asyncio
    async def test_reports_a_non_200_status(self):
        client = _fake_client(_Resp(409))

        with _patched(client):
            result = await _auth().create_user("a@example.com", "pw")

        assert result == {"error": "Supabase API error: 409"}

    @pytest.mark.asyncio
    async def test_reports_a_network_failure(self):
        client = _fake_client(raises=RuntimeError("offline"))

        with _patched(client):
            result = await _auth().create_user("a@example.com", "pw")

        assert "Failed to create user" in result["error"]


class TestGetUser:
    @pytest.mark.asyncio
    async def test_reports_missing_configuration(self):
        assert await _auth(configured=False).get_user("u-1") == {
            "error": "Supabase configuration missing"
        }

    @pytest.mark.asyncio
    async def test_returns_the_user_on_success(self):
        client = _fake_client(_Resp(200, {"id": "u-1", "email": "a@example.com"}))

        with _patched(client):
            result = await _auth().get_user("u-1")

        assert result["id"] == "u-1"

    @pytest.mark.asyncio
    async def test_reports_a_non_200_status(self):
        client = _fake_client(_Resp(404))

        with _patched(client):
            result = await _auth().get_user("missing")

        assert result == {"error": "Supabase API error: 404"}

    @pytest.mark.asyncio
    async def test_reports_a_network_failure(self):
        client = _fake_client(raises=RuntimeError("offline"))

        with _patched(client):
            result = await _auth().get_user("u-1")

        assert "Failed to get user" in result["error"]


class TestGenerateMagicLink:
    @pytest.mark.asyncio
    async def test_raises_when_unconfigured(self):
        with pytest.raises(RuntimeError, match="configuration missing"):
            await _auth(configured=False).generate_magic_link("a@example.com")

    @pytest.mark.asyncio
    async def test_returns_the_token_hash(self):
        client = _fake_client(_Resp(200, {"hashed_token": "abc123"}))

        with _patched(client):
            token_hash = await _auth().generate_magic_link("a@example.com")

        assert token_hash == "abc123"
        assert client.post.await_args.kwargs["json"]["type"] == "magiclink"

    @pytest.mark.asyncio
    async def test_raises_when_no_token_hash_is_returned(self):
        client = _fake_client(_Resp(200, {}))

        with _patched(client):
            with pytest.raises(RuntimeError, match="no token hash"):
                await _auth().generate_magic_link("a@example.com")

    @pytest.mark.asyncio
    async def test_raises_on_a_non_200_status(self):
        client = _fake_client(_Resp(422))

        with _patched(client):
            with pytest.raises(RuntimeError, match="422"):
                await _auth().generate_magic_link("a@example.com")

    @pytest.mark.asyncio
    async def test_wraps_a_network_failure(self):
        client = _fake_client(raises=RuntimeError("offline"))

        with _patched(client):
            with pytest.raises(RuntimeError, match="Failed to mint Supabase session"):
                await _auth().generate_magic_link("a@example.com")


class TestVerifyJwtToken:
    @pytest.mark.asyncio
    async def test_reports_missing_configuration(self):
        result = await _auth(configured=False).verify_jwt_token("t")

        assert result == {"error": "Supabase configuration missing"}

    @pytest.mark.asyncio
    async def test_valid_token_returns_the_user(self):
        client = _fake_client(_Resp(200, {"id": "u-1"}))

        with _patched(client):
            result = await _auth().verify_jwt_token("t")

        assert result == {"valid": True, "user": {"id": "u-1"}}

    @pytest.mark.asyncio
    async def test_invalid_token_is_reported(self):
        client = _fake_client(_Resp(401))

        with _patched(client):
            result = await _auth().verify_jwt_token("bad")

        assert result["valid"] is False
        assert "401" in result["error"]

    @pytest.mark.asyncio
    async def test_a_network_failure_is_reported_as_invalid(self):
        client = _fake_client(raises=RuntimeError("offline"))

        with _patched(client):
            result = await _auth().verify_jwt_token("t")

        assert result["valid"] is False
        assert "Token verification failed" in result["error"]


# ---------------------------------------------------------------------------
# SupabaseDatabase
# ---------------------------------------------------------------------------


class TestExecuteQuery:
    @pytest.mark.asyncio
    async def test_reports_missing_configuration(self):
        result = await _db(configured=False).execute_query("users", {})

        assert result == {"error": "Supabase configuration missing"}

    @pytest.mark.asyncio
    async def test_returns_rows_on_success(self):
        client = _fake_client(_Resp(200, [{"id": 1}]))

        with _patched(client):
            result = await _db().execute_query("users", {"select": "*"})

        assert result == {"data": [{"id": 1}]}
        assert client.get.await_args.kwargs["params"] == {"select": "*"}

    @pytest.mark.asyncio
    async def test_reports_a_non_200_status(self):
        client = _fake_client(_Resp(400))

        with _patched(client):
            result = await _db().execute_query("users", {})

        assert result == {"error": "Supabase API error: 400"}

    @pytest.mark.asyncio
    async def test_reports_a_network_failure(self):
        client = _fake_client(raises=RuntimeError("offline"))

        with _patched(client):
            result = await _db().execute_query("users", {})

        assert "Query execution failed" in result["error"]


class TestInsertData:
    @pytest.mark.asyncio
    async def test_reports_missing_configuration(self):
        assert await _db(configured=False).insert_data("users", {"name": "x"}) == {
            "error": "Supabase configuration missing"
        }

    @pytest.mark.asyncio
    async def test_returns_the_inserted_row_on_201(self):
        client = _fake_client(_Resp(201, [{"id": 1, "name": "x"}]))

        with _patched(client):
            result = await _db().insert_data("users", {"name": "x"})

        assert result == {"data": [{"id": 1, "name": "x"}]}

    @pytest.mark.asyncio
    async def test_reports_a_non_201_status(self):
        client = _fake_client(_Resp(400))

        with _patched(client):
            result = await _db().insert_data("users", {"name": "x"})

        assert result == {"error": "Supabase API error: 400"}

    @pytest.mark.asyncio
    async def test_reports_a_network_failure(self):
        client = _fake_client(raises=RuntimeError("offline"))

        with _patched(client):
            result = await _db().insert_data("users", {"name": "x"})

        assert "Insert failed" in result["error"]


class TestUpdateData:
    @pytest.mark.asyncio
    async def test_reports_missing_configuration(self):
        result = await _db(configured=False).update_data("users", {"name": "y"}, "id", "1")

        assert result == {"error": "Supabase configuration missing"}

    @pytest.mark.asyncio
    async def test_returns_the_updated_row(self):
        client = _fake_client(_Resp(200, [{"id": 1, "name": "y"}]))

        with _patched(client):
            result = await _db().update_data("users", {"name": "y"}, "id", "1")

        assert result == {"data": [{"id": 1, "name": "y"}]}
        assert "id=eq.1" in client.patch.await_args.kwargs["params"]

    @pytest.mark.asyncio
    async def test_reports_a_non_200_status(self):
        client = _fake_client(_Resp(404))

        with _patched(client):
            result = await _db().update_data("users", {"name": "y"}, "id", "1")

        assert result == {"error": "Supabase API error: 404"}

    @pytest.mark.asyncio
    async def test_reports_a_network_failure(self):
        client = _fake_client(raises=RuntimeError("offline"))

        with _patched(client):
            result = await _db().update_data("users", {"name": "y"}, "id", "1")

        assert "Update failed" in result["error"]


class TestDeleteData:
    @pytest.mark.asyncio
    async def test_reports_missing_configuration(self):
        result = await _db(configured=False).delete_data("users", "id", "1")

        assert result == {"error": "Supabase configuration missing"}

    @pytest.mark.asyncio
    async def test_returns_success_on_204(self):
        client = _fake_client(_Resp(204))

        with _patched(client):
            result = await _db().delete_data("users", "id", "1")

        assert result == {"success": True}
        assert "id=eq.1" in client.delete.await_args.kwargs["params"]

    @pytest.mark.asyncio
    async def test_reports_a_non_204_status(self):
        client = _fake_client(_Resp(403))

        with _patched(client):
            result = await _db().delete_data("users", "id", "1")

        assert result == {"error": "Supabase API error: 403"}

    @pytest.mark.asyncio
    async def test_reports_a_network_failure(self):
        client = _fake_client(raises=RuntimeError("offline"))

        with _patched(client):
            result = await _db().delete_data("users", "id", "1")

        assert "Delete failed" in result["error"]


# ---------------------------------------------------------------------------
# SupabaseStorage
# ---------------------------------------------------------------------------


class TestUploadFile:
    @pytest.mark.asyncio
    async def test_reports_missing_configuration(self):
        result = await _storage(configured=False).upload_file("bucket", "f.txt", b"data")

        assert result == {"error": "Supabase configuration missing"}

    @pytest.mark.asyncio
    async def test_returns_the_upload_result(self):
        client = _fake_client(_Resp(200, {"Key": "bucket/f.txt"}))

        with _patched(client):
            result = await _storage().upload_file("bucket", "f.txt", b"data", "text/plain")

        assert result == {"data": {"Key": "bucket/f.txt"}}
        assert client.post.await_args.kwargs["content"] == b"data"
        assert client.post.await_args.kwargs["headers"]["Content-Type"] == "text/plain"

    @pytest.mark.asyncio
    async def test_defaults_content_type_to_octet_stream(self):
        client = _fake_client(_Resp(200, {}))

        with _patched(client):
            await _storage().upload_file("bucket", "f.bin", b"data")

        assert client.post.await_args.kwargs["headers"]["Content-Type"] == (
            "application/octet-stream"
        )

    @pytest.mark.asyncio
    async def test_reports_a_non_200_status(self):
        client = _fake_client(_Resp(413))

        with _patched(client):
            result = await _storage().upload_file("bucket", "f.txt", b"data")

        assert result == {"error": "Supabase Storage error: 413"}

    @pytest.mark.asyncio
    async def test_reports_a_network_failure(self):
        client = _fake_client(raises=RuntimeError("offline"))

        with _patched(client):
            result = await _storage().upload_file("bucket", "f.txt", b"data")

        assert "Upload failed" in result["error"]


class TestGetFileUrl:
    @pytest.mark.asyncio
    async def test_reports_missing_configuration(self):
        result = await _storage(configured=False).get_file_url("bucket", "f.txt")

        assert result == {"error": "Supabase configuration missing"}

    @pytest.mark.asyncio
    async def test_builds_the_public_url(self):
        result = await _storage().get_file_url("bucket", "f.txt")

        assert result["url"] == "https://proj.supabase.co/storage/v1/object/public/bucket/f.txt"
        assert result["bucket"] == "bucket"
        assert result["path"] == "f.txt"


# ---------------------------------------------------------------------------
# get_supabase_config
# ---------------------------------------------------------------------------


class TestGetSupabaseConfig:
    def test_reports_which_settings_are_present(self):
        config: Dict[str, Any] = get_supabase_config()

        assert set(config) == {
            "url",
            "service_role_key",
            "anon_key",
            "database_url",
            "enabled",
        }
        assert isinstance(config["enabled"], bool)
        # database_url always resolves to something (Supabase or the SQLite
        # fallback), so this must always be true regardless of environment.
        assert config["database_url"] is True
