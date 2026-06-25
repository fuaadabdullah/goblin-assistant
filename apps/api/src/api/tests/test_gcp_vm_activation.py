from __future__ import annotations

import base64
from pathlib import Path

import pytest

from api.providers.base import ProviderResult
from api.providers.dispatcher import ProviderDispatcher
from api.providers.provider_config_runtime import ProviderToml
from api.providers.vertex_provider import VertexAIProvider


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

    repo_root = Path(__file__).resolve().parents[5]
    provider_toml = ProviderToml.load(repo_root / "config" / "providers.toml")
    gcp_vm_cfg = provider_toml.providers["gcp_vm"].model_dump()

    dispatcher = ProviderDispatcher(configs={"gcp_vm": gcp_vm_cfg})

    assert dispatcher.is_configured("gcp_vm")
    assert dispatcher.provider_ids(include_hidden=False) == ["gcp_vm"]
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
