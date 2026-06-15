from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from api.integrations.secrets.base import Secret, SecretBackendError, SecretMetadata
from api.integrations.secrets.bitwarden_adapter import BitwardenAdapter
from api.integrations.secrets.bitwarden_mapping import item_to_secret


@pytest.mark.asyncio
async def test_run_bw_command_forwards_adapter_state(monkeypatch):
    adapter = BitwardenAdapter(session_token="token-1", server_url="https://bw.example", timeout=17)

    captured: dict[str, object] = {}

    async def fake_run(command, **kwargs):
        captured["command"] = command
        captured.update(kwargs)
        return "ok"

    monkeypatch.setattr(
        "api.integrations.secrets.bitwarden_adapter.run_bw_command",
        fake_run,
    )

    result = await adapter._run_bw_command(["status"])

    assert result == "ok"
    assert captured["command"] == ["status"]
    assert captured["session_token"] == "token-1"
    assert captured["server_url"] == "https://bw.example"
    assert captured["timeout"] == 17


@pytest.mark.asyncio
async def test_get_secret_uses_existing_facade_seams(monkeypatch):
    adapter = BitwardenAdapter()
    expected = Secret("folder/item", {"value": "secret"}, SecretMetadata())

    monkeypatch.setattr(adapter, "_ensure_authenticated", AsyncMock())
    monkeypatch.setattr(adapter, "_get_cached_secret", AsyncMock(return_value=None))
    monkeypatch.setattr(adapter, "_path_to_item_id", lambda path: ("folder/item", "password"))
    monkeypatch.setattr(adapter, "_fetch_item_for_path", AsyncMock(return_value={"id": "item-1"}))
    monkeypatch.setattr(adapter, "_item_to_secret", lambda item, field_name: expected)
    cache_mock = AsyncMock()
    monkeypatch.setattr(adapter, "_cache_secret", cache_mock)

    result = await adapter.get_secret("folder/item.password")

    assert result is expected
    cache_mock.assert_awaited_once_with("folder/item.password", expected, None)


@pytest.mark.asyncio
async def test_put_secret_rejects_field_updates(monkeypatch):
    adapter = BitwardenAdapter()
    monkeypatch.setattr(adapter, "_ensure_authenticated", AsyncMock())
    monkeypatch.setattr(adapter, "_path_to_item_id", lambda path: ("folder/item", "password"))

    with pytest.raises(SecretBackendError, match="specific fields"):
        await adapter.put_secret("folder/item.password", {"value": "next"})


def test_item_to_secret_reads_custom_field_by_name():
    secret = item_to_secret(
        {
            "id": "item-1",
            "name": "db-creds",
            "fields": [{"name": "api_key", "value": "abc123"}],
        },
        field_name="api_key",
    )

    assert secret.data == {"value": "abc123"}
