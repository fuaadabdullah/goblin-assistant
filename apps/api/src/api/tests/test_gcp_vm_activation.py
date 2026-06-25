from __future__ import annotations

from pathlib import Path

from api.providers.dispatcher import ProviderDispatcher
from api.providers.provider_config_runtime import ProviderToml


def test_gcp_vm_family_wires_self_hosted_backends(monkeypatch) -> None:
    monkeypatch.setenv("OLLAMA_GCP_ENDPOINT", "http://gcp-ollama.example:11434")
    monkeypatch.setenv("LLAMACPP_GCP_ENDPOINT", "http://gcp-llamacpp.example:8000")
    monkeypatch.setenv("VERTEX_AI_PROJECT", "goblin-assistant-479511")
    monkeypatch.setenv("GCP_SERVICE_ACCOUNT_KEY", "eyJ0eXBlIjoic2VydmljZV9hY2NvdW50In0=")

    repo_root = Path(__file__).resolve().parents[5]
    provider_toml = ProviderToml.load(repo_root / "config" / "providers.toml")
    gcp_vm_cfg = provider_toml.providers["gcp_vm"].model_dump()

    dispatcher = ProviderDispatcher(configs={"gcp_vm": gcp_vm_cfg})

    assert dispatcher.is_configured("gcp_vm")
    assert dispatcher.provider_ids(include_hidden=False) == ["gcp_vm"]

    provider = dispatcher.get_provider("gcp_vm")
    assert [backend_id for backend_id, _ in provider.warmup_targets()] == [
        "gcp_vm.ollama",
        "gcp_vm.llamacpp",
        "gcp_vm.colab",
        "gcp_vm.vertex",
    ]
