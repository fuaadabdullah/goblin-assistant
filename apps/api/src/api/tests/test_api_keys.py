"""
Tests for API Key Store abstraction layer.

Covers:
- APIKeyStore ABC constraints
- FileAPIKeyStore (get/set/edge cases)
- SecretManagerAPIKeyStore (initialization errors)
- create_api_key_store factory function
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from api.storage.api_keys import (
    APIKeyStore,
    FileAPIKeyStore,
    SecretManagerAPIKeyStore,
    create_api_key_store,
)

# ---------------------------------------------------------------------------
# APIKeyStore ABC
# ---------------------------------------------------------------------------


class TestAPIKeyStoreABC:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            APIKeyStore()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# FileAPIKeyStore
# ---------------------------------------------------------------------------


class TestFileAPIKeyStore:
    def test_initializes_with_custom_path(self):
        store = FileAPIKeyStore(path="/tmp/test_keys.json")
        assert str(store.path) == "/tmp/test_keys.json"

    def test_warns_in_production(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            with pytest.warns(UserWarning, match="file-based API key"):
                FileAPIKeyStore(path="/tmp/warn_test.json")

    @pytest.mark.asyncio
    async def test_get_returns_none_when_file_missing(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=True) as tf:
            path = tf.name
        # File doesn't exist after deletion
        store = FileAPIKeyStore(path=path)
        result = await store.get("openai")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get_roundtrip(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tf:
            tf.write("{}")
            path = tf.name

        try:
            store = FileAPIKeyStore(path=path)
            await store.set("openai", "sk-abc123")
            result = await store.get("openai")
            assert result == "sk-abc123"

            # Verify file content
            with open(path) as f:  # noqa: ASYNC230
                data = json.load(f)
            assert data["openai"] == "sk-abc123"
        finally:
            Path(path).unlink(missing_ok=True)  # noqa: ASYNC240

    @pytest.mark.asyncio
    async def test_set_overwrites_existing(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tf:
            json.dump({"openai": "sk-old"}, tf)
            path = tf.name

        try:
            store = FileAPIKeyStore(path=path)
            await store.set("openai", "sk-new")
            result = await store.get("openai")
            assert result == "sk-new"
        finally:
            Path(path).unlink(missing_ok=True)  # noqa: ASYNC240

    @pytest.mark.asyncio
    async def test_get_returns_none_on_corrupt_json(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tf:
            tf.write("not valid json")
            path = tf.name

        try:
            store = FileAPIKeyStore(path=path)
            result = await store.get("anthropic")
            assert result is None
        finally:
            Path(path).unlink(missing_ok=True)  # noqa: ASYNC240

    @pytest.mark.asyncio
    async def test_set_handles_corrupt_existing_file(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tf:
            tf.write("{corrupt")
            path = tf.name

        try:
            store = FileAPIKeyStore(path=path)
            await store.set("groq", "gsk-test")
            result = await store.get("groq")
            assert result == "gsk-test"
        finally:
            Path(path).unlink(missing_ok=True)  # noqa: ASYNC240


# ---------------------------------------------------------------------------
# SecretManagerAPIKeyStore
# ---------------------------------------------------------------------------


class TestSecretManagerAPIKeyStore:
    def test_raises_without_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="VAULT_URL and VAULT_TOKEN"):
                SecretManagerAPIKeyStore()

    def test_raises_without_token(self):
        with patch.dict(os.environ, {"VAULT_URL": "http://vault:8200"}, clear=True):
            with pytest.raises(ValueError, match="VAULT_URL and VAULT_TOKEN"):
                SecretManagerAPIKeyStore()

    def test_raises_without_url(self):
        with patch.dict(os.environ, {"VAULT_TOKEN": "s.test123"}, clear=True):
            with pytest.raises(ValueError, match="VAULT_URL and VAULT_TOKEN"):
                SecretManagerAPIKeyStore()

    def test_accepts_explicit_params(self):
        store = SecretManagerAPIKeyStore(vault_url="http://vault:8200", token="s.test123")
        assert store.vault_url == "http://vault:8200"
        assert store.token == "s.test123"

    def test_uses_env_vars(self):
        with patch.dict(
            os.environ,
            {"VAULT_URL": "http://vault:8200", "VAULT_TOKEN": "s.envtoken"},
            clear=True,
        ):
            store = SecretManagerAPIKeyStore()
            assert store.vault_url == "http://vault:8200"
            assert store.token == "s.envtoken"

    def test_get_client_raises_without_hvac(self):
        with patch.dict(
            os.environ,
            {"VAULT_URL": "http://vault:8200", "VAULT_TOKEN": "s.test"},
            clear=True,
        ):
            store = SecretManagerAPIKeyStore()
            # hvac not installed or mocked as missing
            with patch.dict("sys.modules", {"hvac": None}):
                with pytest.raises(RuntimeError, match="hvac package is required"):
                    store._get_client()

    def test_get_client_auth_failure(self):
        with patch.dict(
            os.environ,
            {"VAULT_URL": "http://vault:8200", "VAULT_TOKEN": "s.bad"},
            clear=True,
        ):
            store = SecretManagerAPIKeyStore()
            mock_hvac = MagicMock()
            mock_client = MagicMock()
            mock_client.is_authenticated.return_value = False
            mock_hvac.Client.return_value = mock_client

            with patch.dict("sys.modules", {"hvac": mock_hvac}):
                # Need to actually import via the patched module

                with patch("importlib.import_module", return_value=mock_hvac):
                    with pytest.raises(PermissionError, match="Vault authentication failed"):
                        store._get_client()


# ---------------------------------------------------------------------------
# create_api_key_store factory
# ---------------------------------------------------------------------------


class TestCreateAPIKeyStore:
    def test_creates_secret_manager_in_production(self):
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "production",
                "VAULT_URL": "http://vault:8200",
                "VAULT_TOKEN": "s.test",
            },
            clear=True,
        ):
            store = create_api_key_store()
            assert isinstance(store, SecretManagerAPIKeyStore)

    def test_creates_file_store_in_development(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            store = create_api_key_store()
            assert isinstance(store, FileAPIKeyStore)

    def test_creates_file_store_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            store = create_api_key_store()
            assert isinstance(store, FileAPIKeyStore)
