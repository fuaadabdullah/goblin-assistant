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
from .domain import ProviderMetadata, capabilities_from_config_list
from .google_cloud_provider import GoogleCloudProvider
from .google_cloud_selfhosted_provider import GoogleCloudSelfhostedProvider
from .mock_provider import MockProvider
from .ollama_provider import OllamaProvider
from .openai_compatible import OpenAICompatibleProvider
from .openai_provider import OpenAIProvider
from .provider_config_runtime import ProviderConfig, ProviderToml, load_provider_config
from .rovo_dev_provider import RovoDevProvider
from .siliconeflow import SiliconeFlowProvider

ProviderFactory = Callable[[str, Dict[str, Any]], ProviderAdapter]
ProviderMetadataSource = Callable[[], Dict[str, Dict[str, Any]]]

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


def provider_metadata_from_runtime_config(
    provider_id: str, config: "ProviderRuntimeConfig"
) -> ProviderMetadata:
    """Build the typed ProviderMetadata domain object from a resolved runtime config."""
    limits: Dict[str, int] = {}
    for key in ("max_input_tokens", "max_output_tokens", "max_batch_size"):
        value = config.raw.get(key)
        if isinstance(value, int) and value > 0:
            limits[key] = value

    return ProviderMetadata(
        provider_id=provider_id,
        display_name=config.name or provider_id,
        capabilities=capabilities_from_config_list(config.capabilities),
        default_model=config.default_model or None,
        models=tuple(config.models),
        limits=limits,  # type: ignore[arg-type]
        configured=config.is_configured(),
        extra={},
    )


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


def _load_provider_metadata_source() -> Dict[str, Dict[str, Any]]:
    try:
        provider_toml = load_provider_config(use_cache=True)
    except Exception:
        return {}

    configs: Dict[str, Dict[str, Any]] = {}
    for provider_id, provider_config in provider_toml.providers.items():
        if not getattr(provider_config, "is_active", True):
            continue
        if isinstance(provider_config, ProviderConfig):
            configs[provider_id] = provider_config.model_dump()
        else:
            configs[provider_id] = dict(provider_config or {})
    return configs


_provider_metadata_source: ProviderMetadataSource = _load_provider_metadata_source


def set_provider_metadata_source(source: ProviderMetadataSource) -> None:
    """Register the canonical provider metadata source for model catalogs."""
    global _provider_metadata_source
    _provider_metadata_source = source


def current_provider_metadata_configs() -> Dict[str, Dict[str, Any]]:
    """Return provider metadata without importing the dispatcher facade."""
    return _provider_metadata_source()


def _normalize_provider_token(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _supported_models_for_provider(cfg: Dict[str, Any]) -> set[str]:
    supported: set[str] = set()

    default_model = str(cfg.get("default_model", "")).strip()
    if default_model:
        supported.add(default_model)

    for model_name in cfg.get("models", []):
        model = str(model_name).strip()
        if model:
            supported.add(model)

    for backend in cfg.get("backends", []):
        if not isinstance(backend, dict):
            continue
        for model_name in backend.get("models", []):
            model = str(model_name).strip()
            if model:
                supported.add(model)

    return supported


def validate_model_alias_targets(
    *,
    provider_toml: Any,
    provider_configs: Dict[str, Dict[str, Any]],
    logger: Any,
) -> None:
    """Warn about model aliases that point to unknown providers or models."""
    if provider_toml is None:
        return

    provider_aliases = {
        _normalize_provider_token(alias): _normalize_provider_token(target)
        for alias, target in getattr(provider_toml, "provider_aliases", {}).items()
        if str(alias).strip() and str(target).strip()
    }

    for alias, alias_config in getattr(provider_toml, "model_aliases", {}).items():
        provider = _normalize_provider_token(str(getattr(alias_config, "provider", "") or ""))
        model = str(getattr(alias_config, "model", "") or "").strip()
        if not provider or not model:
            continue

        canonical_provider = provider_aliases.get(provider, provider)
        provider_cfg = provider_configs.get(canonical_provider)
        if provider_cfg is None:
            logger.warning(
                "model_alias_target_provider_missing",
                alias=alias,
                provider=canonical_provider,
                model=model,
            )
            continue

        supported_models = _supported_models_for_provider(provider_cfg)
        if model not in supported_models:
            logger.warning(
                "model_alias_target_model_missing",
                alias=alias,
                provider=canonical_provider,
                model=model,
                supported_models=sorted(supported_models),
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

    def validate_model_alias_targets(
        self,
        *,
        provider_toml: Any,
        provider_configs: Dict[str, Dict[str, Any]],
        logger: Any,
    ) -> None:
        validate_model_alias_targets(
            provider_toml=provider_toml,
            provider_configs=provider_configs,
            logger=logger,
        )

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
    "ProviderMetadataSource",
    "ProviderRegistry",
    "ProviderRuntimeConfig",
    "build_factories_from_class_map",
    "current_provider_metadata_configs",
    "provider_metadata_from_runtime_config",
    "set_provider_metadata_source",
    "validate_model_alias_targets",
]
