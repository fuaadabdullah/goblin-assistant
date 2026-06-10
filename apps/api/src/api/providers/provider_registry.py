"""Provider registry and runtime config wiring for provider adapters."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, Dict

from pydantic import BaseModel, Field

from .aliyun_provider import AliyunProvider
from .anthropic_provider import AnthropicProvider
from .azure_provider import AzureOpenAIProvider
from .base import BaseProvider
from .contracts import ProviderAdapter
from .google_cloud_provider import GoogleCloudProvider
from .google_cloud_selfhosted_provider import GoogleCloudSelfhostedProvider
from .mock_provider import MockProvider
from .ollama_provider import OllamaProvider
from .openai_compatible import OpenAICompatibleProvider
from .openai_provider import OpenAIProvider
from .provider_config_runtime import ProviderConfig, ProviderToml
from .rovo_dev_provider import RovoDevProvider
from .siliconeflow import SiliconeFlowProvider

ProviderFactory = Callable[[str, Dict[str, Any]], ProviderAdapter]

DEFAULT_PROVIDER_CLASS_MAP: Dict[str, type[BaseProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "groq": OpenAICompatibleProvider,
    "siliconeflow": SiliconeFlowProvider,
    "deepseek": OpenAICompatibleProvider,
    "gemini": OpenAICompatibleProvider,
    "azure_openai": AzureOpenAIProvider,
    "aliyun": AliyunProvider,
    "together": OpenAICompatibleProvider,
    "replicate": OpenAICompatibleProvider,
    "huggingface": OpenAICompatibleProvider,
    "cohere": OpenAICompatibleProvider,
    "ollama_local": OllamaProvider,
    "gcp_vllm": GoogleCloudProvider,
    "gcp_vm": GoogleCloudSelfhostedProvider,
    "mock": MockProvider,
    "rovo_dev": RovoDevProvider,
}


def _gcs_any_backend_configured(backends: list) -> bool:
    """Return True if at least one google_cloud_selfhosted backend has its
    required env vars set."""
    from .google_cloud_selfhosted_provider import _backend_is_configured

    return any(_backend_is_configured(bc) for bc in backends)


class ProviderRuntimeConfig(BaseModel):
    """Typed provider config with environment resolution."""

    provider_id: str
    name: str = ""
    endpoint: str = ""
    endpoint_env: str = ""
    api_key_env: str = ""
    default_model: str = ""
    default_deployment: str = ""
    models: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    priority_tier: int = 999
    tier: str = "cloud"
    local_routing: bool = False
    selectable_requires_env: bool = False
    force_fallback: bool = False
    hidden: bool = False
    project_env: str = ""
    default_timeout_ms: int = 0
    health_check_timeout_ms: int = 5_000
    raw: Dict[str, Any] = Field(default_factory=dict)

    resolved_endpoint: str = ""
    resolved_endpoint_env_value: str = ""
    resolved_api_key: str = ""
    resolved_project_value: str = ""
    resolved_vertex_credentials: bool = False
    resolved_azure_endpoint: str = ""
    resolved_azure_deployment: str = ""

    @classmethod
    def from_source(
        cls,
        provider_id: str,
        source: Dict[str, Any],
    ) -> "ProviderRuntimeConfig":
        raw = dict(source or {})
        endpoint_env = str(raw.get("endpoint_env", "") or "").strip()
        api_key_env = str(raw.get("api_key_env", "") or "").strip()
        project_env = str(raw.get("project_env", "") or "").strip()

        endpoint_env_value = os.getenv(endpoint_env, "").strip() if endpoint_env else ""
        fallback_env = f"PROVIDER_{provider_id.upper()}_ENDPOINT"
        if not endpoint_env_value:
            endpoint_env_value = os.getenv(fallback_env, "").strip()
        resolved_endpoint = endpoint_env_value or str(raw.get("endpoint", "") or "").strip()
        resolved_api_key = os.getenv(api_key_env, "").strip() if api_key_env else ""

        resolved_project_value = (
            os.getenv("VERTEX_AI_PROJECT", "").strip()
            or os.getenv("GCP_PROJECT_ID", "").strip()
            or (os.getenv(project_env, "").strip() if project_env else "")
        )
        resolved_vertex_credentials = bool(
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
            or os.getenv("VERTEX_AI_SERVICE_ACCOUNT_JSON", "").strip()
            or os.getenv("GCP_SERVICE_ACCOUNT_KEY", "").strip()
        )

        default_model = str(raw.get("default_model", "") or "").strip()
        default_deployment = str(raw.get("default_deployment", "") or "").strip()
        resolved_azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", resolved_endpoint).strip()
        resolved_azure_deployment = os.getenv(
            "AZURE_DEPLOYMENT_ID",
            default_deployment or default_model,
        ).strip()

        models = raw.get("models", [])
        capabilities = raw.get("capabilities", [])

        return cls(
            provider_id=provider_id,
            name=str(raw.get("name", provider_id) or provider_id),
            endpoint=str(raw.get("endpoint", "") or "").strip(),
            endpoint_env=endpoint_env,
            api_key_env=api_key_env,
            default_model=default_model,
            default_deployment=default_deployment,
            models=[str(item) for item in models] if isinstance(models, list) else [],
            capabilities=(
                [str(item) for item in capabilities] if isinstance(capabilities, list) else []
            ),
            priority_tier=int(raw.get("priority_tier", 999) or 999),
            tier=str(raw.get("tier", "cloud") or "cloud"),
            local_routing=bool(raw.get("local_routing", False)),
            selectable_requires_env=bool(raw.get("selectable_requires_env", False)),
            force_fallback=bool(raw.get("force_fallback", False)),
            hidden=bool(raw.get("hidden", False)),
            project_env=project_env,
            default_timeout_ms=int(raw.get("default_timeout_ms", 0) or 0),
            health_check_timeout_ms=int(raw.get("health_check_timeout_ms", 5000) or 5000),
            raw=raw,
            resolved_endpoint=resolved_endpoint,
            resolved_endpoint_env_value=endpoint_env_value,
            resolved_api_key=resolved_api_key,
            resolved_project_value=resolved_project_value,
            resolved_vertex_credentials=resolved_vertex_credentials,
            resolved_azure_endpoint=resolved_azure_endpoint,
            resolved_azure_deployment=resolved_azure_deployment,
        )

    def to_provider_dict(self) -> Dict[str, Any]:
        cfg = dict(self.raw)
        cfg["provider_id"] = self.provider_id
        cfg["name"] = self.name or self.provider_id
        cfg["endpoint"] = self.resolved_endpoint
        cfg["endpoint_env"] = self.endpoint_env or None
        cfg["api_key_env"] = self.api_key_env or None
        return cfg

    def is_configured(self) -> bool:
        if self.provider_id == "mock":
            return True
        if self.provider_id in ("gcp_vm", "google_cloud_selfhosted"):
            return _gcs_any_backend_configured(self.raw.get("backends", []))
        if self.provider_id == "azure_openai":
            return bool(
                self.resolved_api_key
                and self.resolved_azure_endpoint
                and self.resolved_azure_deployment
            )
        if self.selectable_requires_env:
            return bool(self.resolved_endpoint_env_value)
        if self.api_key_env:
            return bool(self.resolved_api_key)
        if self.tier == "self_hosted":
            return bool(self.resolved_endpoint_env_value)
        return bool(self.resolved_endpoint)


def _factory(provider_cls: type[BaseProvider]) -> ProviderFactory:
    def create(provider_id: str, config: Dict[str, Any]) -> ProviderAdapter:
        return provider_cls(provider_id, config)

    return create


def build_factories_from_class_map(
    class_map: Dict[str, type[BaseProvider]],
) -> Dict[str, ProviderFactory]:
    return {provider_id: _factory(provider_cls) for provider_id, provider_cls in class_map.items()}


_DEFAULT_FACTORIES: Dict[str, ProviderFactory] = build_factories_from_class_map(
    DEFAULT_PROVIDER_CLASS_MAP
)


class ProviderRegistry:
    """Registry of provider factories keyed by canonical provider id."""

    def __init__(
        self,
        factories: Dict[str, ProviderFactory] | None = None,
    ) -> None:
        self._factories: Dict[str, ProviderFactory] = dict(factories or _DEFAULT_FACTORIES)

    @classmethod
    def default(cls) -> "ProviderRegistry":
        return cls()

    def register(self, provider_id: str, factory: ProviderFactory) -> None:
        self._factories[provider_id] = factory

    def has(self, provider_id: str) -> bool:
        return provider_id in self._factories

    def _source_to_dict(
        self,
        source: ProviderConfig | Dict[str, Any],
    ) -> Dict[str, Any]:
        if isinstance(source, ProviderConfig):
            return source.model_dump()
        return dict(source or {})

    def runtime_config(
        self,
        provider_id: str,
        source: ProviderConfig | Dict[str, Any],
    ) -> ProviderRuntimeConfig:
        return ProviderRuntimeConfig.from_source(provider_id, self._source_to_dict(source))

    def create_from_source(
        self,
        provider_id: str,
        source: ProviderConfig | Dict[str, Any],
    ) -> ProviderAdapter:
        factory = self._factories.get(provider_id)
        if factory is None:
            raise KeyError(f"Unknown provider factory: {provider_id}")
        runtime_cfg = self.runtime_config(provider_id, source)
        return factory(provider_id, runtime_cfg.to_provider_dict())

    def build(self, config: ProviderToml) -> Dict[str, ProviderAdapter]:
        providers: Dict[str, ProviderAdapter] = {}
        for provider_id, provider_config in config.providers.items():
            try:
                providers[provider_id] = self.create_from_source(
                    provider_id,
                    provider_config,
                )
            except (KeyError, ValueError, TypeError, RuntimeError):
                continue
        return providers


__all__ = [
    "DEFAULT_PROVIDER_CLASS_MAP",
    "ProviderFactory",
    "ProviderRegistry",
    "ProviderRuntimeConfig",
    "build_factories_from_class_map",
]
