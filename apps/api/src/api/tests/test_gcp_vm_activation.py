from __future__ import annotations

import base64
from pathlib import Path

import pytest

from api.providers import vertex_provider
from api.providers.base import ProviderResult
from api.providers.dispatcher import ProviderDispatcher
from api.providers.provider_config_runtime import ProviderToml
from api.providers.vertex_provider import VertexAIProvider

REPO_ROOT = Path(__file__).resolve().parents[5]


@pytest.mark.asyncio
async def test_gcp_vm_vertex_default_model_routes_real_provider(monkeypatch) -> None:
    monkeypatch.delenv("OLLAMA_GCP_ENDPOINT", raising=False)
    monkeypatch.delenv("OLLAMA_GCP_URL", raising=False)
    monkeypatch.delenv("LLAMACPP_GCP_ENDPOINT", raising=False)
    monkeypatch.delenv("COLAB_WORKER_ENDPOINT", raising=False)
    monkeypatch.delenv("COLAB_WORKER_API_KEY", raising=False)
    monkeypatch.setenv("VERTEX_AI_PROJECT", "goblin-assistant-489711")
    monkeypatch.setenv(
        "VERTEX_AI_SERVICE_ACCOUNT_JSON",
        base64.b64encode(
            b'{"type":"authorized_user","client_id":"test","client_secret":"test","refresh_token":"test","quota_project_id":"goblin-assistant-489711"}'
        ).decode("ascii"),
    )

    provider_toml = ProviderToml.load(REPO_ROOT / "config" / "providers.toml")
    gcp_vm_cfg = provider_toml.providers["gcp_vm"].model_dump()

    dispatcher = ProviderDispatcher(configs={"gcp_vm": gcp_vm_cfg})

    assert dispatcher.is_configured("gcp_vm")
    # gcp_vm is intentionally hidden + inactive in config/providers.toml since
    # its preemptible VM backends were terminated (2026-01-11) — it's kept
    # configured for direct/explicit dispatch (this test), just excluded from
    # default visible listings. include_hidden=True reflects that.
    assert dispatcher.provider_ids(include_hidden=True) == ["gcp_vm"]
    assert gcp_vm_cfg["default_model"] == "gemini-2.5-flash"

    provider = dispatcher.get_provider("gcp_vm")
    assert [backend_id for backend_id, _ in provider.warmup_targets()][0] == "gcp_vm.vertex"

    async def _fake_invoke(self, messages=None, model=None, **kwargs):
        _ = messages, kwargs
        return ProviderResult(
            ok=True,
            provider=self.provider_id,
            model=model or self.default_model,
            text="ok",
        )

    monkeypatch.setattr(VertexAIProvider, "invoke", _fake_invoke)

    result = await provider.invoke(messages=[{"role": "user", "content": "hi"}])

    assert result.ok is True
    assert result.provider == "gcp_vm"
    assert result.model == "gemini-2.5-flash"


def test_configure_google_credentials_survives_name_too_long(monkeypatch, tmp_path):
    """Regression test: inline JSON credential content set directly as
    GOOGLE_APPLICATION_CREDENTIALS is long enough to exceed a single path
    component's NAME_MAX on Linux (e.g. ext4's 255-byte limit), so
    Path.exists() raises OSError[ENAMETOOLONG] instead of returning False.
    Reproduced on Render; not reproducible on macOS for the same string."""
    credentials_json = (
        '{"type": "authorized_user", "client_id": "test", '
        '"client_secret": "test", "refresh_token": "test"}'
    )
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", credentials_json)
    monkeypatch.delenv("VERTEX_AI_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.delenv("GCP_SERVICE_ACCOUNT_KEY", raising=False)

    service_account_file = tmp_path / "vertex_service_account.json"
    monkeypatch.setattr(vertex_provider, "_VERTEX_SERVICE_ACCOUNT_FILE", service_account_file)

    def _raise_name_too_long(self):
        raise OSError(36, "File name too long")

    monkeypatch.setattr(vertex_provider.Path, "exists", _raise_name_too_long)

    vertex_provider._configure_google_credentials()

    assert service_account_file.read_text(encoding="utf-8") == credentials_json
