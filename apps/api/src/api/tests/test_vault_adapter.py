"""Tests for VaultAdapter — the HashiCorp Vault secrets backend.

The adapter wraps hvac's synchronous client, supports both KV v1 and v2, and
translates Vault's exception types into the repository's own secret errors.
That translation and the v1/v2 branching are what these tests pin down; the
hvac client itself is always a fake.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hvac.exceptions import Forbidden, InvalidPath, VaultError

from api.integrations.secrets.base import (
    SecretBackendError,
    SecretNotFoundError,
    SecretUnauthorizedError,
    SecretValidationError,
)
from api.integrations.secrets.vault_adapter import VaultAdapter, _parse_vault_time

_KV2_METADATA: Dict[str, Any] = {
    "created_time": "2026-01-01T00:00:00Z",
    "updated_time": "2026-01-02T00:00:00Z",
    "version": 3,
    "custom_metadata": {"owner": "platform"},
}


@pytest.fixture
def adapter() -> VaultAdapter:
    instance = VaultAdapter("https://vault.example:8200/", mount_point="kv")
    # The cache spins a background sweeper; these tests drive it directly.
    instance.cache = MagicMock()
    instance.cache.get_secret = AsyncMock(return_value=None)
    instance.cache.set_secret = AsyncMock()
    instance.cache.invalidate_path = AsyncMock()
    instance.cache.stop = AsyncMock()
    return instance


def _client(*, authenticated: bool = True) -> MagicMock:
    client = MagicMock()
    client.is_authenticated.return_value = authenticated
    return client


def _bind(adapter: VaultAdapter, client: MagicMock, *, kv_version: int = 2) -> None:
    """Attach a fake client and pin the KV version so tests skip detection."""
    adapter._client = client
    adapter._kv_version = kv_version


# ---------------------------------------------------------------------------
# _parse_vault_time
# ---------------------------------------------------------------------------


class TestParseVaultTime:
    def test_parses_a_zulu_timestamp(self):
        parsed = _parse_vault_time("2026-01-01T00:00:00Z")

        assert isinstance(parsed, datetime)
        assert parsed.year == 2026

    def test_empty_input_is_none(self):
        assert _parse_vault_time("") is None
        assert _parse_vault_time(None) is None

    def test_unparsable_input_is_none_rather_than_raising(self):
        assert _parse_vault_time("not-a-timestamp") is None


# ---------------------------------------------------------------------------
# Construction and connection handling
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_trailing_slash_is_stripped_from_the_url(self, adapter):
        assert adapter.vault_url == "https://vault.example:8200"

    def test_mount_point_is_kept(self, adapter):
        assert adapter.mount_point == "kv"

    @pytest.mark.asyncio
    async def test_client_is_created_once_and_reused(self, adapter):
        session = MagicMock(closed=False)

        with (
            patch.object(adapter, "_get_session", AsyncMock(return_value=session)),
            patch("api.integrations.secrets.vault_adapter.hvac.Client") as client_cls,
        ):
            first = await adapter._get_client()
            second = await adapter._get_client()

        assert first is second
        client_cls.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_is_reused_while_open(self, adapter):
        existing = MagicMock(closed=False)
        adapter._session = existing

        assert await adapter._get_session() is existing

    @pytest.mark.asyncio
    async def test_a_closed_session_is_replaced(self, adapter):
        adapter._session = MagicMock(closed=True)

        with patch("api.integrations.secrets.vault_adapter.aiohttp.ClientSession") as session_cls:
            await adapter._get_session()

        session_cls.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_releases_the_session_and_client(self, adapter):
        session = MagicMock(closed=False)
        session.close = AsyncMock()
        adapter._session = session
        adapter._client = MagicMock()

        await adapter.close()

        session.close.assert_awaited_once()
        adapter.cache.stop.assert_awaited_once()
        assert adapter._session is None
        assert adapter._client is None

    @pytest.mark.asyncio
    async def test_close_is_safe_when_nothing_is_open(self, adapter):
        await adapter.close()

        assert adapter._client is None


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class TestAuthentication:
    @pytest.mark.asyncio
    async def test_token_auth_succeeds(self, adapter):
        client = _client()
        _bind(adapter, client)

        assert await adapter.authenticate_with_token("s.token") is True
        assert client.token == "s.token"

    @pytest.mark.asyncio
    async def test_token_auth_rejects_an_invalid_token(self, adapter):
        _bind(adapter, _client(authenticated=False))

        with pytest.raises(SecretUnauthorizedError):
            await adapter.authenticate_with_token("bad")

    @pytest.mark.asyncio
    async def test_approle_auth_returns_credentials_with_expiry(self, adapter):
        client = _client()
        client.auth.approle.login.return_value = {
            "auth": {"client_token": "s.approle", "lease_duration": 3600}
        }
        _bind(adapter, client)

        credentials = await adapter.authenticate_with_approle("role", "secret")

        assert credentials.token == "s.approle"
        assert credentials.expires_at is not None

    @pytest.mark.asyncio
    async def test_approle_without_a_lease_has_no_expiry(self, adapter):
        client = _client()
        client.auth.approle.login.return_value = {
            "auth": {"client_token": "s.approle", "lease_duration": 0}
        }
        _bind(adapter, client)

        credentials = await adapter.authenticate_with_approle("role", "secret")

        assert credentials.expires_at is None

    @pytest.mark.asyncio
    async def test_approle_auth_failure_is_translated(self, adapter):
        client = _client(authenticated=False)
        client.auth.approle.login.return_value = {"auth": {"client_token": "t"}}
        _bind(adapter, client)

        with pytest.raises(SecretUnauthorizedError):
            await adapter.authenticate_with_approle("role", "secret")

    @pytest.mark.asyncio
    async def test_ensure_authenticated_raises_when_unauthenticated(self, adapter):
        _bind(adapter, _client(authenticated=False))

        with pytest.raises(SecretUnauthorizedError):
            await adapter._ensure_authenticated()


# ---------------------------------------------------------------------------
# KV version detection
# ---------------------------------------------------------------------------


class TestDetectKvVersion:
    @pytest.mark.asyncio
    async def test_detected_version_is_cached(self, adapter):
        adapter._kv_version = 2
        adapter._client = MagicMock()

        assert await adapter._detect_kv_version() == 2
        adapter._client.sys.list_mounted_secrets_engines.assert_not_called()

    @pytest.mark.asyncio
    async def test_reads_the_version_from_the_mount_options(self, adapter):
        client = _client()
        client.sys.list_mounted_secrets_engines.return_value = {"kv": {"options": {"version": "2"}}}
        adapter._client = client

        assert await adapter._detect_kv_version() == 2

    @pytest.mark.asyncio
    async def test_defaults_to_v1_when_the_mount_is_absent(self, adapter):
        client = _client()
        client.sys.list_mounted_secrets_engines.return_value = {"other": {}}
        adapter._client = client

        assert await adapter._detect_kv_version() == 1

    @pytest.mark.asyncio
    async def test_defaults_to_v1_when_options_omit_the_version(self, adapter):
        client = _client()
        client.sys.list_mounted_secrets_engines.return_value = {"kv": {"options": {}}}
        adapter._client = client

        assert await adapter._detect_kv_version() == 1

    @pytest.mark.asyncio
    async def test_an_unexpected_version_falls_back_to_v1(self, adapter):
        client = _client()
        client.sys.list_mounted_secrets_engines.return_value = {"kv": {"options": {"version": "9"}}}
        adapter._client = client

        assert await adapter._detect_kv_version() == 1

    @pytest.mark.asyncio
    async def test_a_failing_lookup_is_a_backend_error(self, adapter):
        client = _client()
        client.sys.list_mounted_secrets_engines.side_effect = RuntimeError("no perms")
        adapter._client = client

        with pytest.raises(SecretBackendError):
            await adapter._detect_kv_version()


# ---------------------------------------------------------------------------
# Metadata builders
# ---------------------------------------------------------------------------


class TestMetadataBuilders:
    def test_kv2_metadata_carries_versions_and_custom_fields(self, adapter):
        metadata = adapter._build_kv2_metadata(_KV2_METADATA)

        assert metadata.version == 3
        assert metadata.custom_metadata == {"owner": "platform"}
        assert metadata.backend_specific["vault_kv_version"] == 2
        assert metadata.backend_specific["mount_point"] == "kv"
        assert metadata.created_at is not None

    def test_kv1_metadata_is_deliberately_sparse(self, adapter):
        metadata = adapter._build_kv1_metadata()

        assert metadata.version is None
        assert metadata.created_at is None
        assert metadata.backend_specific["vault_kv_version"] == 1


# ---------------------------------------------------------------------------
# get_secret
# ---------------------------------------------------------------------------


class TestGetSecret:
    @pytest.mark.asyncio
    async def test_reads_a_kv2_secret_and_caches_it(self, adapter):
        client = _client()
        client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"value": "s3cret"}, "metadata": _KV2_METADATA}
        }
        _bind(adapter, client, kv_version=2)

        secret = await adapter.get_secret("app/db")

        assert secret.data == {"value": "s3cret"}
        assert secret.metadata.version == 3
        adapter.cache.set_secret.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_requests_a_specific_version_when_asked(self, adapter):
        client = _client()
        client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"value": "old"}, "metadata": _KV2_METADATA}
        }
        _bind(adapter, client, kv_version=2)

        await adapter.get_secret("app/db", version=2)

        assert client.secrets.kv.v2.read_secret_version.call_args.kwargs["version"] == 2

    @pytest.mark.asyncio
    async def test_reads_a_kv1_secret(self, adapter):
        client = _client()
        client.secrets.kv.v1.read_secret.return_value = {"data": {"value": "s3cret"}}
        _bind(adapter, client, kv_version=1)

        secret = await adapter.get_secret("app/db")

        assert secret.data == {"value": "s3cret"}
        assert secret.metadata.backend_specific["vault_kv_version"] == 1

    @pytest.mark.asyncio
    async def test_a_cache_hit_skips_vault_entirely(self, adapter):
        client = _client()
        _bind(adapter, client, kv_version=2)
        adapter.cache.get_secret = AsyncMock(
            return_value={
                "data": {"value": "cached"},
                "metadata": {
                    "created_at": None,
                    "updated_at": None,
                    "version": 1,
                    "custom_metadata": {},
                    "backend_specific": {},
                },
            }
        )

        secret = await adapter.get_secret("app/db")

        assert secret.data == {"value": "cached"}
        client.secrets.kv.v2.read_secret_version.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_path_becomes_not_found(self, adapter):
        client = _client()
        client.secrets.kv.v2.read_secret_version.side_effect = InvalidPath()
        _bind(adapter, client, kv_version=2)

        with pytest.raises(SecretNotFoundError):
            await adapter.get_secret("missing")

    @pytest.mark.asyncio
    async def test_forbidden_becomes_unauthorized(self, adapter):
        client = _client()
        client.secrets.kv.v2.read_secret_version.side_effect = Forbidden()
        _bind(adapter, client, kv_version=2)

        with pytest.raises(SecretUnauthorizedError):
            await adapter.get_secret("app/db")

    @pytest.mark.asyncio
    async def test_a_vault_error_becomes_a_backend_error(self, adapter):
        client = _client()
        client.secrets.kv.v2.read_secret_version.side_effect = VaultError("sealed")
        _bind(adapter, client, kv_version=2)

        with pytest.raises(SecretBackendError):
            await adapter.get_secret("app/db")

    @pytest.mark.asyncio
    async def test_an_unexpected_error_becomes_a_backend_error(self, adapter):
        client = _client()
        client.secrets.kv.v2.read_secret_version.side_effect = KeyError("data")
        _bind(adapter, client, kv_version=2)

        with pytest.raises(SecretBackendError):
            await adapter.get_secret("app/db")


# ---------------------------------------------------------------------------
# put_secret
# ---------------------------------------------------------------------------


class TestPutSecret:
    @pytest.mark.asyncio
    async def test_writes_a_kv2_secret_and_refreshes_the_cache(self, adapter):
        client = _client()
        client.secrets.kv.v2.create_or_update_secret.return_value = {
            "data": {"metadata": _KV2_METADATA}
        }
        _bind(adapter, client, kv_version=2)

        secret = await adapter.put_secret("app/db", {"value": "new"})

        assert secret.data == {"value": "new"}
        adapter.cache.invalidate_path.assert_awaited_once_with("app/db")
        adapter.cache.set_secret.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_passes_a_cas_version_for_conditional_writes(self, adapter):
        client = _client()
        client.secrets.kv.v2.create_or_update_secret.return_value = {
            "data": {"metadata": _KV2_METADATA}
        }
        _bind(adapter, client, kv_version=2)

        await adapter.put_secret("app/db", {"value": "new"}, version=4)

        written = client.secrets.kv.v2.create_or_update_secret.call_args.kwargs["secret"]
        assert written["options"] == {"cas": 4}

    @pytest.mark.asyncio
    async def test_custom_metadata_is_forwarded(self, adapter):
        client = _client()
        client.secrets.kv.v2.create_or_update_secret.return_value = {
            "data": {"metadata": _KV2_METADATA}
        }
        _bind(adapter, client, kv_version=2)

        await adapter.put_secret("app/db", {"value": "new"}, metadata={"owner": "me"})

        written = client.secrets.kv.v2.create_or_update_secret.call_args.kwargs["secret"]
        assert written["metadata"] == {"owner": "me"}

    @pytest.mark.asyncio
    async def test_writes_a_kv1_secret(self, adapter):
        client = _client()
        _bind(adapter, client, kv_version=1)

        secret = await adapter.put_secret("app/db", {"value": "new"})

        client.secrets.kv.v1.create_or_update_secret.assert_called_once()
        assert secret.metadata.backend_specific["vault_kv_version"] == 1

    @pytest.mark.asyncio
    async def test_empty_data_is_rejected(self, adapter):
        _bind(adapter, _client(), kv_version=2)

        # SecretValidationError is re-wrapped by the broad handler below it.
        with pytest.raises((SecretValidationError, SecretBackendError)):
            await adapter.put_secret("app/db", {})

    @pytest.mark.asyncio
    async def test_forbidden_becomes_unauthorized(self, adapter):
        client = _client()
        client.secrets.kv.v2.create_or_update_secret.side_effect = Forbidden()
        _bind(adapter, client, kv_version=2)

        with pytest.raises(SecretUnauthorizedError):
            await adapter.put_secret("app/db", {"value": "v"})

    @pytest.mark.asyncio
    async def test_a_vault_error_becomes_a_backend_error(self, adapter):
        client = _client()
        client.secrets.kv.v2.create_or_update_secret.side_effect = VaultError("sealed")
        _bind(adapter, client, kv_version=2)

        with pytest.raises(SecretBackendError):
            await adapter.put_secret("app/db", {"value": "v"})


# ---------------------------------------------------------------------------
# list_secrets
# ---------------------------------------------------------------------------


class TestListSecrets:
    @pytest.mark.asyncio
    async def test_lists_kv2_keys_and_drops_directories(self, adapter):
        client = _client()
        client.secrets.kv.v2.list_secrets.return_value = {"data": {"keys": ["a", "nested/", "b"]}}
        _bind(adapter, client, kv_version=2)

        assert await adapter.list_secrets("app") == ["a", "b"]

    @pytest.mark.asyncio
    async def test_applies_the_limit(self, adapter):
        client = _client()
        client.secrets.kv.v2.list_secrets.return_value = {"data": {"keys": ["a", "b", "c"]}}
        _bind(adapter, client, kv_version=2)

        assert await adapter.list_secrets("app", limit=2) == ["a", "b"]

    @pytest.mark.asyncio
    async def test_lists_kv1_keys(self, adapter):
        client = _client()
        client.secrets.kv.v1.list_secrets.return_value = {"data": {"keys": ["a", "dir/"]}}
        _bind(adapter, client, kv_version=1)

        assert await adapter.list_secrets("app") == ["a"]

    @pytest.mark.asyncio
    async def test_an_empty_response_yields_no_paths(self, adapter):
        client = _client()
        client.secrets.kv.v2.list_secrets.return_value = {}
        _bind(adapter, client, kv_version=2)

        assert await adapter.list_secrets("app") == []

    @pytest.mark.asyncio
    async def test_kv1_empty_response_yields_no_paths(self, adapter):
        client = _client()
        client.secrets.kv.v1.list_secrets.return_value = None
        _bind(adapter, client, kv_version=1)

        assert await adapter.list_secrets("app") == []

    @pytest.mark.asyncio
    async def test_forbidden_becomes_unauthorized(self, adapter):
        client = _client()
        client.secrets.kv.v2.list_secrets.side_effect = Forbidden()
        _bind(adapter, client, kv_version=2)

        with pytest.raises(SecretUnauthorizedError):
            await adapter.list_secrets("app")

    @pytest.mark.asyncio
    async def test_a_vault_error_becomes_a_backend_error(self, adapter):
        client = _client()
        client.secrets.kv.v2.list_secrets.side_effect = VaultError("sealed")
        _bind(adapter, client, kv_version=2)

        with pytest.raises(SecretBackendError):
            await adapter.list_secrets("app")

    @pytest.mark.asyncio
    async def test_an_unexpected_error_becomes_a_backend_error(self, adapter):
        client = _client()
        client.secrets.kv.v2.list_secrets.side_effect = RuntimeError("boom")
        _bind(adapter, client, kv_version=2)

        with pytest.raises(SecretBackendError):
            await adapter.list_secrets("app")


# ---------------------------------------------------------------------------
# delete_secret
# ---------------------------------------------------------------------------


class TestDeleteSecret:
    @pytest.mark.asyncio
    async def test_kv2_deletes_the_latest_version_by_default(self, adapter):
        client = _client()
        _bind(adapter, client, kv_version=2)

        await adapter.delete_secret("app/db")

        client.secrets.kv.v2.delete_latest_version_of_secret.assert_called_once()
        adapter.cache.invalidate_path.assert_awaited_once_with("app/db")

    @pytest.mark.asyncio
    async def test_kv2_deletes_a_named_version(self, adapter):
        client = _client()
        _bind(adapter, client, kv_version=2)

        await adapter.delete_secret("app/db", version=2)

        assert client.secrets.kv.v2.delete_secret_versions.call_args.kwargs["versions"] == [2]

    @pytest.mark.asyncio
    async def test_kv1_deletes_outright(self, adapter):
        client = _client()
        _bind(adapter, client, kv_version=1)

        await adapter.delete_secret("app/db")

        client.secrets.kv.v1.delete_secret.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_path_becomes_not_found(self, adapter):
        client = _client()
        client.secrets.kv.v2.delete_latest_version_of_secret.side_effect = InvalidPath()
        _bind(adapter, client, kv_version=2)

        with pytest.raises(SecretNotFoundError):
            await adapter.delete_secret("missing")

    @pytest.mark.asyncio
    async def test_forbidden_becomes_unauthorized(self, adapter):
        client = _client()
        client.secrets.kv.v2.delete_latest_version_of_secret.side_effect = Forbidden()
        _bind(adapter, client, kv_version=2)

        with pytest.raises(SecretUnauthorizedError):
            await adapter.delete_secret("app/db")

    @pytest.mark.asyncio
    async def test_a_vault_error_becomes_a_backend_error(self, adapter):
        client = _client()
        client.secrets.kv.v2.delete_latest_version_of_secret.side_effect = VaultError("sealed")
        _bind(adapter, client, kv_version=2)

        with pytest.raises(SecretBackendError):
            await adapter.delete_secret("app/db")


# ---------------------------------------------------------------------------
# rotate_secret
# ---------------------------------------------------------------------------


class TestRotateSecret:
    @pytest.mark.asyncio
    async def test_generates_a_new_value_and_preserves_the_structure(self, adapter):
        existing = MagicMock()
        existing.data = {"value": "old", "username": "app"}

        with (
            patch.object(adapter, "get_secret", AsyncMock(return_value=existing)),
            patch.object(adapter, "put_secret", AsyncMock()) as put,
        ):
            new_value = await adapter.rotate_secret("app/db")

        assert len(new_value) == 32
        written = put.await_args.args[1]
        assert written["value"] == new_value
        assert written["username"] == "app"

    @pytest.mark.asyncio
    async def test_a_failure_becomes_a_backend_error(self, adapter):
        with patch.object(
            adapter, "get_secret", AsyncMock(side_effect=SecretNotFoundError("gone"))
        ):
            with pytest.raises(SecretBackendError):
                await adapter.rotate_secret("app/db")


# ---------------------------------------------------------------------------
# health
# ---------------------------------------------------------------------------


class TestHealth:
    @pytest.mark.asyncio
    async def test_healthy_when_authenticated_and_unsealed(self, adapter):
        client = _client()
        client.sys.read_health_status.return_value = {"sealed": False, "initialized": True}
        _bind(adapter, client, kv_version=2)

        health = await adapter.health()

        assert health["status"] == "healthy"
        assert health["authenticated"] is True
        assert health["kv_version"] == 2
        assert health["mount_point"] == "kv"

    @pytest.mark.asyncio
    async def test_degraded_when_not_authenticated(self, adapter):
        client = _client(authenticated=False)
        client.sys.read_health_status.return_value = {"sealed": False, "initialized": True}
        _bind(adapter, client, kv_version=2)

        assert (await adapter.health())["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_unhealthy_when_sealed(self, adapter):
        client = _client()
        client.sys.read_health_status.return_value = {"sealed": True, "initialized": True}
        _bind(adapter, client, kv_version=2)

        assert (await adapter.health())["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_an_unreadable_status_is_treated_as_sealed(self, adapter):
        client = _client()
        client.sys.read_health_status.side_effect = RuntimeError("no route")
        _bind(adapter, client, kv_version=2)

        health = await adapter.health()

        assert health["vault_sealed"] is True
        assert health["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_a_total_failure_reports_unhealthy_with_the_error(self, adapter):
        with patch.object(adapter, "_get_client", AsyncMock(side_effect=RuntimeError("no vault"))):
            health = await adapter.health()

        assert health["status"] == "unhealthy"
        assert "no vault" in health["error"]
