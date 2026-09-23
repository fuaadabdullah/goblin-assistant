"""Unit tests for the bitwarden-sdk-backed BitwardenAdapter."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from api.integrations.secrets.base import SecretNotFoundError, SecretUnauthorizedError
from api.integrations.secrets.bitwarden_adapter import (
    BitwardenAdapter,
    _data_to_value_note,
    _value_note_to_data,
)

_ORG_ID = "00000000-0000-0000-0000-000000000001"


def _resp(success=True, data=None, error_message=None):
    return SimpleNamespace(success=success, data=data, error_message=error_message)


def _identifier(secret_id: str, key: str):
    return SimpleNamespace(id=secret_id, key=key)


def _secret(secret_id: str, key: str, value: str, note=None, project_id=None):
    return SimpleNamespace(
        id=secret_id,
        key=key,
        value=value,
        note=note,
        project_id=project_id,
        organization_id=_ORG_ID,
        creation_date=None,
        revision_date=None,
    )


class _FakeSecrets:
    def __init__(self, secrets_by_key=None):
        self.secrets_by_key = dict(secrets_by_key or {})

    def list(self, organization_id):
        data = SimpleNamespace(data=[_identifier(s.id, s.key) for s in self.secrets_by_key.values()])
        return _resp(data=data)

    def get(self, secret_id):
        for secret in self.secrets_by_key.values():
            if secret.id == secret_id:
                return _resp(data=secret)
        return _resp(success=False, error_message="not found")

    def create(self, organization_id, key, value, note, project_ids=None):
        project_id = str(project_ids[0]) if project_ids else None
        secret = _secret("new-id", key, value, note, project_id)
        self.secrets_by_key[key] = secret
        return _resp(data=secret)

    def update(self, organization_id, secret_id, key, value, note, project_ids=None):
        project_id = str(project_ids[0]) if project_ids else None
        secret = _secret(secret_id, key, value, note, project_id)
        self.secrets_by_key[key] = secret
        return _resp(data=secret)

    def delete(self, ids):
        for key, secret in list(self.secrets_by_key.items()):
            if secret.id in ids:
                del self.secrets_by_key[key]
        return _resp()


class _FakeProjects:
    def list(self, organization_id):
        return _resp()


class _FakeClient:
    def __init__(self, secrets_by_key=None):
        self._secrets = _FakeSecrets(secrets_by_key)

    def secrets(self):
        return self._secrets

    def projects(self):
        return _FakeProjects()


def make_adapter(secrets_by_key=None) -> BitwardenAdapter:
    adapter = BitwardenAdapter(access_token="tok", organization_id=_ORG_ID)
    adapter._client = _FakeClient(secrets_by_key)
    return adapter


@pytest.mark.asyncio
async def test_put_and_get_secret_roundtrip():
    adapter = make_adapter()
    await adapter.put_secret("db-password", {"value": "s3cret"})
    secret = await adapter.get_secret("db-password")
    assert secret.path == "db-password"
    assert secret.data == {"value": "s3cret"}


@pytest.mark.asyncio
async def test_get_secret_not_found():
    adapter = make_adapter()
    with pytest.raises(SecretNotFoundError):
        await adapter.get_secret("missing")


@pytest.mark.asyncio
async def test_put_secret_updates_existing():
    adapter = make_adapter({"db-password": _secret("id-1", "db-password", "old")})
    await adapter.put_secret("db-password", {"value": "new"})
    secret = await adapter.get_secret("db-password")
    assert secret.data["value"] == "new"


@pytest.mark.asyncio
async def test_list_secrets_prefix():
    adapter = make_adapter(
        {
            "api/openai": _secret("1", "api/openai", "v1"),
            "api/aws": _secret("2", "api/aws", "v2"),
            "db/password": _secret("3", "db/password", "v3"),
        }
    )
    assert await adapter.list_secrets(prefix="api/") == ["api/openai", "api/aws"]


@pytest.mark.asyncio
async def test_delete_secret():
    adapter = make_adapter({"db-password": _secret("1", "db-password", "v")})
    await adapter.delete_secret("db-password")
    with pytest.raises(SecretNotFoundError):
        await adapter.get_secret("db-password")


@pytest.mark.asyncio
async def test_rotate_secret():
    adapter = make_adapter({"db-password": _secret("1", "db-password", "old")})
    new_value = await adapter.rotate_secret("db-password")
    assert new_value and new_value != "old"
    assert (await adapter.get_secret("db-password")).data["value"] == new_value


def test_data_value_note_roundtrip():
    assert _data_to_value_note({"value": "x"}) == ("x", None)
    assert _value_note_to_data("x", None) == {"value": "x"}
    assert _data_to_value_note({"value": "x", "env": "prod"}) == ("x", '{"env": "prod"}')
    assert _value_note_to_data("x", '{"env": "prod"}') == {"value": "x", "env": "prod"}


def test_build_client_requires_token_and_org():
    with pytest.raises(SecretUnauthorizedError, match="ACCESS_TOKEN"):
        BitwardenAdapter(access_token=None, organization_id=_ORG_ID)._build_client()
    with pytest.raises(SecretUnauthorizedError, match="ORGANIZATION_ID"):
        BitwardenAdapter(access_token="tok", organization_id=None)._build_client()


def test_build_client_logs_in(monkeypatch):
    fake_client = MagicMock()
    fake_client.auth.login_access_token.return_value = _resp()
    fake_client_cls = MagicMock(return_value=fake_client)
    monkeypatch.setattr("api.integrations.secrets.bitwarden_adapter.BitwardenClient", fake_client_cls)
    monkeypatch.setattr("api.integrations.secrets.bitwarden_adapter.ClientSettings", MagicMock(return_value="settings"))

    adapter = BitwardenAdapter(access_token="tok", organization_id=_ORG_ID)
    client = adapter._build_client()

    assert client is fake_client
    fake_client.auth.login_access_token.assert_called_once_with("tok")
