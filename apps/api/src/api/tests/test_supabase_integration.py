"""Tests for supabase_integration module — auth, database, and storage operations."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

import api.supabase_integration as supabase_integration
from api.supabase_integration import (
    SupabaseAuth,
    SupabaseDatabase,
    SupabaseStorage,
)

# ──────────────────────────────────────────────────────────────────────────────
# SupabaseAuth Tests
# ──────────────────────────────────────────────────────────────────────────────


def _set_supabase_constants(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        supabase_integration,
        "SUPABASE_URL",
        "https://test.supabase.co",
    )
    monkeypatch.setattr(
        supabase_integration,
        "SUPABASE_SERVICE_ROLE_KEY",
        "service-key",
    )
    monkeypatch.setattr(
        supabase_integration,
        "SUPABASE_ANON_KEY",
        "anon-key",
    )


class TestSupabaseAuth:
    """Test SupabaseAuth class methods."""

    def test_init_with_env_vars(self, monkeypatch):
        """SupabaseAuth initializes with patched module configuration."""
        _set_supabase_constants(monkeypatch)

        auth = SupabaseAuth()
        assert auth.url == "https://test.supabase.co"
        assert auth.anon_key == "anon-key"
        assert auth.service_role_key == "service-key"
        assert auth.api_url == "https://test.supabase.co/auth/v1"

    def test_init_without_env_vars(self, monkeypatch):
        """SupabaseAuth handles missing environment variables gracefully."""
        monkeypatch.setattr(supabase_integration, "SUPABASE_URL", None)
        monkeypatch.setattr(supabase_integration, "SUPABASE_SERVICE_ROLE_KEY", None)
        monkeypatch.setattr(supabase_integration, "SUPABASE_ANON_KEY", None)

        auth = SupabaseAuth()
        assert auth.url is None
        assert auth.anon_key is None
        assert auth.service_role_key is None
        assert auth.api_url is None

    @pytest.mark.asyncio
    async def test_create_user_missing_config(self):
        """create_user returns error when configuration is missing."""
        auth = SupabaseAuth()
        auth.api_url = None
        auth.service_role_key = None

        result = await auth.create_user("test@example.com", "password")

        assert result == {"error": "Supabase configuration missing"}

    @pytest.mark.asyncio
    async def test_create_user_success(self, monkeypatch):
        """create_user returns user data on successful response."""
        auth = SupabaseAuth()
        auth.api_url = "https://test.supabase.co/auth/v1"
        auth.service_role_key = "service-key"

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {"id": "user-123", "email": "test@example.com"}

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = fake_response

        with patch("api.supabase_integration.httpx.AsyncClient", return_value=mock_client):
            result = await auth.create_user("test@example.com", "password", {"name": "Test"})

        assert result["id"] == "user-123"
        assert result["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_create_user_api_error(self, monkeypatch):
        """create_user returns error on non-200 response."""
        auth = SupabaseAuth()
        auth.api_url = "https://test.supabase.co/auth/v1"
        auth.service_role_key = "service-key"

        fake_response = MagicMock()
        fake_response.status_code = 400

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = fake_response

        with patch("api.supabase_integration.httpx.AsyncClient", return_value=mock_client):
            result = await auth.create_user("test@example.com", "password")

        assert "error" in result
        assert "400" in result["error"]

    @pytest.mark.asyncio
    async def test_create_user_exception(self, monkeypatch):
        """create_user returns error on exception."""
        auth = SupabaseAuth()
        auth.api_url = "https://test.supabase.co/auth/v1"
        auth.service_role_key = "service-key"

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.side_effect = httpx.RequestError("Network error")

        with patch("api.supabase_integration.httpx.AsyncClient", return_value=mock_client):
            result = await auth.create_user("test@example.com", "password")

        assert "error" in result
        assert "Failed to create user" in result["error"]

    @pytest.mark.asyncio
    async def test_get_user_success(self, monkeypatch):
        """get_user returns user data on successful response."""
        auth = SupabaseAuth()
        auth.api_url = "https://test.supabase.co/auth/v1"
        auth.service_role_key = "service-key"

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {"id": "user-123", "email": "test@example.com"}

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = fake_response

        with patch("api.supabase_integration.httpx.AsyncClient", return_value=mock_client):
            result = await auth.get_user("user-123")

        assert result["id"] == "user-123"

    @pytest.mark.asyncio
    async def test_verify_jwt_token_valid(self, monkeypatch):
        """verify_jwt_token returns valid=True on successful response."""
        auth = SupabaseAuth()
        auth.api_url = "https://test.supabase.co/auth/v1"
        auth.anon_key = "anon-key"

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {"id": "user-123"}

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = fake_response

        with patch("api.supabase_integration.httpx.AsyncClient", return_value=mock_client):
            result = await auth.verify_jwt_token("token-abc")

        assert result["valid"] is True
        assert result["user"]["id"] == "user-123"

    @pytest.mark.asyncio
    async def test_verify_jwt_token_invalid(self, monkeypatch):
        """verify_jwt_token returns valid=False on non-200 response."""
        auth = SupabaseAuth()
        auth.api_url = "https://test.supabase.co/auth/v1"
        auth.anon_key = "anon-key"

        fake_response = MagicMock()
        fake_response.status_code = 401

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = fake_response

        with patch("api.supabase_integration.httpx.AsyncClient", return_value=mock_client):
            result = await auth.verify_jwt_token("bad-token")

        assert result["valid"] is False
        assert "error" in result


# ──────────────────────────────────────────────────────────────────────────────
# SupabaseDatabase Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestSupabaseDatabase:
    """Test SupabaseDatabase class methods."""

    def test_init_with_env_vars(self, monkeypatch):
        """SupabaseDatabase initializes with patched module configuration."""
        _set_supabase_constants(monkeypatch)

        db = SupabaseDatabase()
        assert db.url == "https://test.supabase.co"
        assert db.service_role_key == "service-key"
        assert db.anon_key == "anon-key"
        assert db.rest_url == "https://test.supabase.co/rest/v1"

    @pytest.mark.asyncio
    async def test_execute_query_missing_config(self):
        """execute_query returns error when configuration is missing."""
        db = SupabaseDatabase()
        db.rest_url = None
        db.service_role_key = None

        result = await db.execute_query("users", {})

        assert result == {"error": "Supabase configuration missing"}

    @pytest.mark.asyncio
    async def test_execute_query_success(self):
        """execute_query returns data on successful response."""
        db = SupabaseDatabase()
        db.rest_url = "https://test.supabase.co/rest/v1"
        db.service_role_key = "service-key"

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = [{"id": 1, "name": "Test"}]

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = fake_response

        with patch("api.supabase_integration.httpx.AsyncClient", return_value=mock_client):
            result = await db.execute_query("users", {"id": "eq.1"})

        assert result == {"data": [{"id": 1, "name": "Test"}]}

    @pytest.mark.asyncio
    async def test_insert_data_success(self):
        """insert_data returns data on successful creation."""
        db = SupabaseDatabase()
        db.rest_url = "https://test.supabase.co/rest/v1"
        db.service_role_key = "service-key"

        fake_response = MagicMock()
        fake_response.status_code = 201
        fake_response.json.return_value = {"id": 1, "name": "New User"}

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = fake_response

        with patch("api.supabase_integration.httpx.AsyncClient", return_value=mock_client):
            result = await db.insert_data("users", {"name": "New User"})

        assert result == {"data": {"id": 1, "name": "New User"}}

    @pytest.mark.asyncio
    async def test_insert_data_error(self):
        """insert_data returns error on non-201 response."""
        db = SupabaseDatabase()
        db.rest_url = "https://test.supabase.co/rest/v1"
        db.service_role_key = "service-key"

        fake_response = MagicMock()
        fake_response.status_code = 400

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = fake_response

        with patch("api.supabase_integration.httpx.AsyncClient", return_value=mock_client):
            result = await db.insert_data("users", {"name": "New User"})

        assert "error" in result

    @pytest.mark.asyncio
    async def test_update_data_success(self):
        """update_data returns data on successful update."""
        db = SupabaseDatabase()
        db.rest_url = "https://test.supabase.co/rest/v1"
        db.service_role_key = "service-key"

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {"id": 1, "name": "Updated"}

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.patch.return_value = fake_response

        with patch("api.supabase_integration.httpx.AsyncClient", return_value=mock_client):
            result = await db.update_data("users", {"name": "Updated"}, "id", "1")

        assert result == {"data": {"id": 1, "name": "Updated"}}

    @pytest.mark.asyncio
    async def test_delete_data_success(self):
        """delete_data returns success on 204 response."""
        db = SupabaseDatabase()
        db.rest_url = "https://test.supabase.co/rest/v1"
        db.service_role_key = "service-key"

        fake_response = MagicMock()
        fake_response.status_code = 204

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.delete.return_value = fake_response

        with patch("api.supabase_integration.httpx.AsyncClient", return_value=mock_client):
            result = await db.delete_data("users", "id", "1")

        assert result == {"success": True}


# ──────────────────────────────────────────────────────────────────────────────
# SupabaseStorage Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestSupabaseStorage:
    """Test SupabaseStorage class methods."""

    def test_init_with_env_vars(self, monkeypatch):
        """SupabaseStorage initializes with patched module configuration."""
        _set_supabase_constants(monkeypatch)

        storage = SupabaseStorage()
        assert storage.url == "https://test.supabase.co"
        assert storage.service_role_key == "service-key"
        assert storage.storage_url == "https://test.supabase.co/storage/v1"

    @pytest.mark.asyncio
    async def test_upload_file_missing_config(self):
        """upload_file returns error when configuration is missing."""
        storage = SupabaseStorage()
        storage.storage_url = None
        storage.service_role_key = None

        result = await storage.upload_file("bucket", "path/file", b"data")

        assert result == {"error": "Supabase configuration missing"}

    @pytest.mark.asyncio
    async def test_upload_file_success(self):
        """upload_file returns data on successful upload."""
        storage = SupabaseStorage()
        storage.storage_url = "https://test.supabase.co/storage/v1"
        storage.service_role_key = "service-key"

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {"path": "path/file"}

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = fake_response

        with patch("api.supabase_integration.httpx.AsyncClient", return_value=mock_client):
            result = await storage.upload_file("bucket", "path/file", b"data")

        assert result == {"data": {"path": "path/file"}}

    @pytest.mark.asyncio
    async def test_upload_file_error(self):
        """upload_file returns error on non-200 response."""
        storage = SupabaseStorage()
        storage.storage_url = "https://test.supabase.co/storage/v1"
        storage.service_role_key = "service-key"

        fake_response = MagicMock()
        fake_response.status_code = 400

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = fake_response

        with patch("api.supabase_integration.httpx.AsyncClient", return_value=mock_client):
            result = await storage.upload_file("bucket", "path/file", b"data")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_file_url_success(self):
        """get_file_url returns public URL."""
        storage = SupabaseStorage()
        storage.storage_url = "https://test.supabase.co/storage/v1"

        result = await storage.get_file_url("bucket", "path/file")

        assert result == {
            "bucket": "bucket",
            "path": "path/file",
            "url": "https://test.supabase.co/storage/v1/object/public/bucket/path/file",
        }


# ──────────────────────────────────────────────────────────────────────────────
# get_supabase_config Tests
# ──────────────────────────────────────────────────────────────────────────────


def test_get_supabase_config_all_present(monkeypatch):
    """get_supabase_config returns all True when all env vars are present."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")

    # Need to reimport the module to pick up the new env vars
    import importlib

    import api.supabase_integration as supa_module

    importlib.reload(supa_module)

    config = supa_module.get_supabase_config()

    assert config["url"] is True
    assert config["service_role_key"] is True
    assert config["anon_key"] is True
    assert config["database_url"] is True
    assert config["enabled"] is True


def test_get_supabase_config_partial(monkeypatch):
    """get_supabase_config returns False for missing env vars."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    import importlib

    import api.supabase_integration as supa_module

    importlib.reload(supa_module)

    config = supa_module.get_supabase_config()

    assert config["url"] is False
    assert config["service_role_key"] is False
    assert config["anon_key"] is False
    assert config["enabled"] is False
