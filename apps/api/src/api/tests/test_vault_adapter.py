from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.integrations.secrets.base import Secret, SecretMetadata
from api.integrations.secrets.vault_adapter import VaultAdapter
from api.integrations.secrets.vault_kv import build_kv2_metadata, list_secret_paths


@pytest.mark.asyncio
async def test_get_client_awaits_session_before_constructing_hvac(monkeypatch):
    adapter = VaultAdapter(vault_url="http://vault.example")
    session = object()
    created = {}

    async def fake_get_session():
        return session

    def fake_client(*, url, verify, session):
        created["url"] = url
        created["verify"] = verify
        created["session"] = session
        return SimpleNamespace()

    monkeypatch.setattr(adapter, "_get_session", fake_get_session)
    monkeypatch.setattr("api.integrations.secrets.vault_adapter.hvac.Client", fake_client)

    client = await adapter._get_client()

    assert client is not None
    assert created["url"] == "http://vault.example"
    assert created["session"] is session


@pytest.mark.asyncio
async def test_close_stops_cache_and_session(monkeypatch):
    adapter = VaultAdapter(vault_url="http://vault.example")
    adapter.cache.stop = AsyncMock()
    adapter._session = SimpleNamespace(closed=False, close=AsyncMock())
    adapter._client = object()

    await adapter.close()

    adapter.cache.stop.assert_awaited_once()
    assert adapter._session is None
    assert adapter._client is None


@pytest.mark.asyncio
async def test_get_secret_uses_facade_seams(monkeypatch):
    adapter = VaultAdapter(vault_url="http://vault.example")
    expected = Secret("secret/path", {"value": "abc"}, SecretMetadata(version=2))

    monkeypatch.setattr(adapter, "_ensure_authenticated", AsyncMock())
    monkeypatch.setattr(adapter, "_detect_kv_version", AsyncMock(return_value=2))
    monkeypatch.setattr(adapter, "_get_cached_secret", AsyncMock(return_value=None))
    monkeypatch.setattr(
        adapter,
        "_read_secret_payload",
        AsyncMock(return_value=({"value": "abc"}, expected.metadata)),
    )
    cache_mock = AsyncMock()
    monkeypatch.setattr(adapter, "_cache_secret", cache_mock)

    result = await adapter.get_secret("secret/path")

    assert result.path == "secret/path"
    assert result.data == {"value": "abc"}
    cache_mock.assert_awaited_once()


def test_list_secret_paths_filters_directory_markers():
    client = SimpleNamespace(
        secrets=SimpleNamespace(
            kv=SimpleNamespace(
                v2=SimpleNamespace(
                    list_secrets=lambda **kwargs: {"data": {"keys": ["a", "nested/", "b"]}}
                ),
                v1=SimpleNamespace(list_secrets=lambda **kwargs: {"data": {"keys": []}}),
            )
        )
    )

    assert list_secret_paths(client, "secret", "", 10, 2) == ["a", "b"]


def test_build_kv2_metadata_keeps_mount_and_version():
    metadata = build_kv2_metadata(
        "secret",
        {
            "created_time": "2026-01-01T00:00:00Z",
            "updated_time": "2026-01-02T00:00:00Z",
            "version": 7,
            "custom_metadata": {"owner": "ops"},
            "cas_version": 6,
        },
    )

    assert metadata.version == 7
    assert metadata.backend_specific["mount_point"] == "secret"
    assert metadata.backend_specific["vault_kv_version"] == 2
