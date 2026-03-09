"""
Authoritative provider dispatcher for Goblin Assistant.

This module is the single source of truth for provider registration,
invocation, routing metadata, health probing, and registry data returned to
the rest of the backend.
"""

from __future__ import annotations

import asyncio
import importlib
import os
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import structlog

from .aliyun_provider import AliyunProvider
from .anthropic_provider import AnthropicProvider
from .azure_provider import AzureOpenAIProvider
from .base import BaseProvider, ProviderResult
from .llamacpp_provider import LlamaCPPProvider
from .mock_provider import MockProvider
from .ollama_provider import OllamaProvider
from .openai_compatible import OpenAICompatibleProvider
from .openai_provider import OpenAIProvider
from .vertex_provider import VertexAIProvider

logger = structlog.get_logger(__name__)

try:
    from dotenv import load_dotenv

    load_dotenv()
    load_dotenv(".env.local")
except ImportError:
    pass

_PROVIDER_ALIASES: Dict[str, str] = {
    "azure": "azure_openai",
    "azure_openai": "azure_openai",
    "azure_openai_provider": "azure_openai",
    "azure_openai_api": "azure_openai",
    "azure_openai_service": "azure_openai",
    "azure_openai_deployment": "azure_openai",
    "azure_openai_resource": "azure_openai",
    "azure_openai_model": "azure_openai",
    "azure_openai_models": "azure_openai",
    "azure_openai_provider_models": "azure_openai",
    "azure_openai_provider_model": "azure_openai",
    "azure_openai_provider_service": "azure_openai",
    "azure_openai_provider_api": "azure_openai",
    "azure_openai_provider_resource": "azure_openai",
    "azure_openai_provider_deployment": "azure_openai",
    "azure_openai_provider_deployments": "azure_openai",
    "azure_openai_provider_resources": "azure_openai",
    "azure_openai_provider_services": "azure_openai",
    "azure_openai_provider_apis": "azure_openai",
    "azure_openai_provider_models_registry": "azure_openai",
    "azure_openai_provider_registry": "azure_openai",
    "azure_openai_provider_catalog": "azure_openai",
    "azure_openai_provider_catalogs": "azure_openai",
    "azure_openai_provider_inference": "azure_openai",
    "azure_openai_provider_runtime": "azure_openai",
    "azure_openai_provider_gateway": "azure_openai",
    "azure_openai_provider_router": "azure_openai",
    "azure_openai_provider_health": "azure_openai",
    "azure_openai_provider_routing": "azure_openai",
    "azure_openai_provider_status": "azure_openai",
    "azure_openai_provider_metadata": "azure_openai",
    "azure_openai_provider_config": "azure_openai",
    "azure_openai_provider_settings": "azure_openai",
    "azure_openai_provider_profile": "azure_openai",
    "azure_openai_provider_profiles": "azure_openai",
    "azure_openai_provider_id": "azure_openai",
    "azure_openai_provider_ids": "azure_openai",
    "azure_openai_provider_alias": "azure_openai",
    "azure_openai_provider_aliases": "azure_openai",
    "azure_openai_provider_key": "azure_openai",
    "azure_openai_provider_keys": "azure_openai",
    "azure_openai_provider_env": "azure_openai",
    "azure_openai_provider_envs": "azure_openai",
    "azure-openai": "azure_openai",
    "vertex": "vertex_ai",
    "vertex-ai": "vertex_ai",
    "google": "gemini",
    "ollama": "ollama_local",
    "ollama-local": "ollama_local",
    "ollama-gcp": "ollama_gcp",
    "ollama-kamatera": "ollama_kamatera",
    "llamacpp": "llamacpp_gcp",
    "llama_cpp": "llamacpp_gcp",
    "llamacpp-gcp": "llamacpp_gcp",
    "llamacpp-kamatera": "llamacpp_kamatera",
}

_MODEL_ALIASES: Dict[str, tuple[str, str]] = {
    "gpt-4o": ("openai", "gpt-4o"),
    "gpt-4o-mini": ("openai", "gpt-4o-mini"),
    "claude-haiku": ("anthropic", "claude-3-5-haiku-latest"),
    "claude-sonnet": ("anthropic", "claude-sonnet-4-20250514"),
    "qwen-max": ("aliyun", "qwen-max"),
    "qwen-plus": ("aliyun", "qwen-plus"),
    "deepseek-chat": ("deepseek", "deepseek-chat"),
    "gemini-flash": ("gemini", "gemini-2.0-flash"),
    "qwen-3b": ("ollama_gcp", "qwen2.5:3b"),
    "qwen-local": ("ollama_local", "qwen2.5:3b"),
}

_VISIBLE_PROVIDER_IDS = {
    "openai",
    "anthropic",
    "groq",
    "siliconeflow",
    "deepseek",
    "gemini",
    "azure_openai",
    "vertex_ai",
    "aliyun",
    "ollama_gcp",
    "llamacpp_gcp",
    "ollama_local",
}

_DEFAULT_PROVIDER_CONFIGS: Dict[str, Dict[str, Any]] = {
    "openai": {
        "name": "OpenAI",
        "endpoint": "https://api.openai.com/v1",
        "endpoint_env": "OPENAI_ENDPOINT",
        "api_key_env": "OPENAI_API_KEY",
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "capabilities": ["chat", "reasoning", "code", "embedding", "image"],
        "priority_tier": 10,
        "tier": "cloud",
    },
    "anthropic": {
        "name": "Anthropic",
        "endpoint": "https://api.anthropic.com",
        "endpoint_env": "ANTHROPIC_ENDPOINT",
        "api_key_env": "ANTHROPIC_API_KEY",
        "default_model": "claude-3-5-haiku-latest",
        "models": ["claude-sonnet-4-20250514", "claude-3-5-haiku-latest"],
        "capabilities": ["chat", "reasoning", "code"],
        "priority_tier": 20,
        "tier": "cloud",
    },
    "groq": {
        "name": "Groq",
        "endpoint": "https://api.groq.com/openai",
        "endpoint_env": "GROQ_ENDPOINT",
        "api_key_env": "GROQ_API_KEY",
        "default_model": "llama-3.3-70b-versatile",
        "models": ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"],
        "capabilities": ["chat", "reasoning", "code"],
        "cost_input_per1k": 0.00059,
        "cost_output_per1k": 0.00079,
        "priority_tier": 30,
        "tier": "cloud",
    },
    "siliconeflow": {
        "name": "SiliconeFlow",
        "endpoint": "https://api.siliconflow.com",
        "endpoint_env": "SILICONEFLOW_ENDPOINT",
        "api_key_env": "SILICONEFLOW_API_KEY",
        "default_model": "Qwen/Qwen2.5-7B-Instruct",
        "models": ["Qwen/Qwen2.5-7B-Instruct", "Qwen/Qwen2.5-Coder-7B-Instruct"],
        "capabilities": ["chat", "reasoning", "code"],
        "cost_input_per1k": 0.00014,
        "cost_output_per1k": 0.00014,
        "priority_tier": 35,
        "tier": "cloud",
    },
    "deepseek": {
        "name": "DeepSeek",
        "endpoint": "https://api.deepseek.com",
        "endpoint_env": "DEEPSEEK_ENDPOINT",
        "api_key_env": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-coder"],
        "capabilities": ["chat", "reasoning", "code"],
        "cost_input_per1k": 0.00027,
        "cost_output_per1k": 0.0011,
        "priority_tier": 40,
        "tier": "cloud",
    },
    "gemini": {
        "name": "Google Gemini",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/openai",
        "endpoint_env": "GEMINI_ENDPOINT",
        "api_key_env": "GOOGLE_AI_API_KEY",
        "default_model": "gemini-2.0-flash",
        "models": ["gemini-2.0-flash", "gemini-2.0-flash-lite"],
        "capabilities": ["chat", "reasoning", "code", "image"],
        "cost_input_per1k": 0.000075,
        "cost_output_per1k": 0.0003,
        "priority_tier": 50,
        "tier": "cloud",
    },
    "azure_openai": {
        "name": "Azure OpenAI",
        "endpoint": "https://goblinos-resource.services.ai.azure.com",
        "endpoint_env": "AZURE_OPENAI_ENDPOINT",
        "api_key_env": "AZURE_API_KEY",
        "default_model": "gpt-4o-mini",
        "default_deployment": "gpt-4o-mini",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4.1"],
        "capabilities": ["chat", "reasoning", "code", "embedding"],
        "priority_tier": 25,
        "tier": "private",
    },
    "vertex_ai": {
        "name": "Google Vertex AI",
        "endpoint_env": "VERTEX_AI_ENDPOINT",
        "default_model": "gemini-2.5-flash",
        "models": ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"],
        "capabilities": ["chat", "reasoning", "code", "image"],
        "priority_tier": 45,
        "tier": "private",
        "project_env": "VERTEX_AI_PROJECT",
    },
    "aliyun": {
        "name": "Aliyun DashScope",
        "endpoint": "https://dashscope-intl.aliyuncs.com/compatible-mode",
        "endpoint_env": "DASHSCOPE_ENDPOINT",
        "api_key_env": "DASHSCOPE_API_KEY",
        "default_model": "qwen-plus",
        "models": ["qwen-turbo", "qwen-plus", "qwen-max"],
        "capabilities": ["chat", "reasoning", "code"],
        "priority_tier": 60,
        "tier": "private",
        "local_routing": True,
    },
    "ollama_gcp": {
        "name": "Ollama GCP",
        "endpoint": "http://34.60.255.199:11434",
        "endpoint_env": "OLLAMA_GCP_ENDPOINT",
        "default_model": "qwen2.5:3b",
        "models": ["qwen2.5:3b", "llama3.2:1b"],
        "capabilities": ["chat", "reasoning", "code"],
        "priority_tier": 70,
        "tier": "self_hosted",
        "selectable_requires_env": True,
    },
    "llamacpp_gcp": {
        "name": "LlamaCPP GCP",
        "endpoint": "http://34.132.226.143:8000",
        "endpoint_env": "LLAMACPP_GCP_ENDPOINT",
        "default_model": "",
        "models": ["qwen2.5-3b-instruct-q4_k_m"],
        "capabilities": ["chat", "reasoning", "code"],
        "priority_tier": 75,
        "tier": "self_hosted",
        "selectable_requires_env": True,
    },
    "ollama_local": {
        "name": "Ollama Local",
        "endpoint": "http://localhost:11434",
        "endpoint_env": "OLLAMA_LOCAL_ENDPOINT",
        "default_model": "qwen2.5:3b",
        "models": ["qwen2.5:3b"],
        "capabilities": ["chat", "reasoning", "code"],
        "priority_tier": 80,
        "tier": "self_hosted",
        "selectable_requires_env": True,
    },
    "ollama_kamatera": {
        "name": "Ollama Kamatera",
        "endpoint": "http://192.175.23.150:8002",
        "endpoint_env": "OLLAMA_KAMATERA_ENDPOINT",
        "default_model": "qwen2.5:latest",
        "models": ["qwen2.5:latest"],
        "capabilities": ["chat", "reasoning", "code"],
        "priority_tier": 99,
        "tier": "self_hosted",
        "selectable_requires_env": True,
        "hidden": True,
    },
    "llamacpp_kamatera": {
        "name": "LlamaCPP Kamatera",
        "endpoint": "http://45.61.51.220:8000",
        "endpoint_env": "KAMATERA_LLAMACPP_ENDPOINT",
        "default_model": "qwen2.5:latest",
        "models": ["qwen2.5:latest"],
        "capabilities": ["chat", "reasoning", "code"],
        "priority_tier": 99,
        "tier": "self_hosted",
        "selectable_requires_env": True,
        "hidden": True,
    },
    "mock": {
        "name": "Mock Provider",
        "endpoint": "mock://localhost",
        "default_model": "mock-gpt",
        "models": ["mock-gpt"],
        "capabilities": ["chat", "reasoning", "code", "embedding"],
        "priority_tier": 999,
        "tier": "mock",
        "hidden": True,
    },
}

_PROVIDER_CLASS_MAP = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "groq": OpenAICompatibleProvider,
    "siliconeflow": OpenAICompatibleProvider,
    "deepseek": OpenAICompatibleProvider,
    "gemini": OpenAICompatibleProvider,
    "azure_openai": AzureOpenAIProvider,
    "vertex_ai": VertexAIProvider,
    "aliyun": AliyunProvider,
    "ollama_gcp": OllamaProvider,
    "ollama_local": OllamaProvider,
    "ollama_kamatera": OllamaProvider,
    "llamacpp_gcp": LlamaCPPProvider,
    "llamacpp_kamatera": LlamaCPPProvider,
    "mock": MockProvider,
}


def _normalize_token(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def canonical_provider_id(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = _normalize_token(value)
    if not normalized:
        return None
    return _PROVIDER_ALIASES.get(normalized, normalized)


class ProviderDispatcher:
    def __init__(self) -> None:
        self._configs = self._load_provider_configs()
        self._providers: Dict[str, BaseProvider] = {}
        self._routing_min_success_rate = self._load_min_success_rate()
        self._build_registry()

    def _load_min_success_rate(self) -> float:
        raw_value = os.getenv("ROUTING_MIN_SUCCESS_RATE", "0.3").strip()
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            return 0.3
        return max(0.0, min(1.0, value))

    def _config_path(self) -> Path:
        return Path(__file__).resolve().parents[2] / "config" / "providers.toml"

    def _read_provider_toml(self) -> Dict[str, Dict[str, Any]]:
        config_path = self._config_path()
        if not config_path.exists():
            return {}

        try:
            try:
                import tomllib

                with open(config_path, "rb") as file_obj:
                    parsed = tomllib.load(file_obj)
            except ImportError:
                toml = importlib.import_module("toml")
                with open(config_path, "r", encoding="utf-8") as file_obj:
                    parsed = toml.load(file_obj)
        except (ImportError, OSError, ValueError, TypeError) as exc:
            logger.warning("provider_config_load_failed", error=str(exc))
            return {}

        providers = parsed.get("providers", {})
        return providers if isinstance(providers, dict) else {}

    def _apply_endpoint_env_overrides(
        self, provider_id: str, provider_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        resolved = dict(provider_config)
        endpoint_env_name = str(resolved.get("endpoint_env", "")).strip()
        fallback_env_name = f"PROVIDER_{provider_id.upper()}_ENDPOINT"

        env_endpoint = ""
        if endpoint_env_name:
            env_endpoint = os.getenv(endpoint_env_name, "").strip()
        if not env_endpoint:
            env_endpoint = os.getenv(fallback_env_name, "").strip()
        if env_endpoint:
            resolved["endpoint"] = env_endpoint

        return resolved

    def _load_provider_configs(self) -> Dict[str, Dict[str, Any]]:
        loaded: Dict[str, Dict[str, Any]] = {
            provider_id: dict(config)
            for provider_id, config in _DEFAULT_PROVIDER_CONFIGS.items()
        }
        for raw_id, raw_config in self._read_provider_toml().items():
            canonical_id = canonical_provider_id(raw_id)
            if canonical_id is None:
                continue
            if canonical_id not in _DEFAULT_PROVIDER_CONFIGS and raw_id not in _DEFAULT_PROVIDER_CONFIGS:
                continue

            merged = dict(_DEFAULT_PROVIDER_CONFIGS.get(canonical_id, {}))
            merged.update(raw_config if isinstance(raw_config, dict) else {})
            merged["provider_id"] = canonical_id
            loaded[canonical_id] = self._apply_endpoint_env_overrides(canonical_id, merged)

        for provider_id, config in list(loaded.items()):
            loaded[provider_id] = self._apply_endpoint_env_overrides(provider_id, config)

        return loaded

    def _build_registry(self) -> None:
        for provider_id, config in self._configs.items():
            provider_class = _PROVIDER_CLASS_MAP.get(provider_id)
            if provider_class is None:
                continue
            try:
                self._providers[provider_id] = provider_class(provider_id, config)
            except Exception as exc:
                logger.warning(
                    "provider_init_failed",
                    provider=provider_id,
                    error=str(exc),
                )

    def list_providers(self, include_hidden: bool = False) -> List[Dict[str, Any]]:
        providers: List[Dict[str, Any]] = []
        for provider_id, config in self._configs.items():
            if config.get("hidden") and not include_hidden:
                continue
            providers.append(
                {
                    "id": provider_id,
                    "name": config.get("name", provider_id),
                    "endpoint": config.get("endpoint", ""),
                    "endpoint_env": config.get("endpoint_env"),
                    "api_key_env": config.get("api_key_env"),
                    "default_model": config.get("default_model", ""),
                    "models": list(config.get("models", [])),
                    "capabilities": list(config.get("capabilities", [])),
                    "priority_tier": int(config.get("priority_tier", 999)),
                    "tier": config.get("tier", "cloud"),
                    "local_routing": bool(config.get("local_routing", False)),
                    "hidden": bool(config.get("hidden", False)),
                }
            )
        providers.sort(key=lambda item: (int(item["priority_tier"]), str(item["id"])))
        return providers

    def provider_ids(self, include_hidden: bool = False) -> List[str]:
        return [item["id"] for item in self.list_providers(include_hidden=include_hidden)]

    def _is_self_hosted(self, config: Dict[str, Any]) -> bool:
        return str(config.get("tier", "")) == "self_hosted"

    def is_configured(self, provider_id: str) -> bool:
        config = self._configs.get(provider_id, {})
        if not config:
            return False

        if provider_id == "mock":
            return True

        if provider_id == "vertex_ai":
            return bool(
                os.getenv("VERTEX_AI_PROJECT", "").strip()
                or config.get("project")
                or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
            )

        if provider_id == "azure_openai":
            api_key_env = str(config.get("api_key_env", "AZURE_API_KEY"))
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", str(config.get("endpoint", ""))).strip()
            deployment = os.getenv(
                "AZURE_DEPLOYMENT_ID",
                str(
                    config.get("deployment_id")
                    or config.get("default_deployment")
                    or config.get("default_model", "")
                ),
            ).strip()
            return bool(os.getenv(api_key_env, "").strip() and endpoint and deployment)

        endpoint_env = str(config.get("endpoint_env", "")).strip()
        if config.get("selectable_requires_env"):
            return bool(endpoint_env and os.getenv(endpoint_env, "").strip())

        api_key_env = str(config.get("api_key_env", "")).strip()
        if api_key_env:
            return bool(os.getenv(api_key_env, "").strip())

        if self._is_self_hosted(config):
            return bool(endpoint_env and os.getenv(endpoint_env, "").strip())

        return bool(str(config.get("endpoint", "")).strip())

    def get_provider(self, provider_id: str) -> BaseProvider:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        provider = self._providers.get(canonical_id)
        if provider is None:
            raise KeyError(f"Unknown provider: {provider_id}")
        return provider

    def get_provider_config(self, provider_id: str) -> Dict[str, Any]:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        return dict(self._configs.get(canonical_id, {}))

    def _provider_costs(self, provider_id: str) -> tuple[float, float]:
        provider = self._providers.get(provider_id)
        if provider is None:
            return (float("inf"), float("inf"))
        return (provider.COST_INPUT_PER_1K, provider.COST_OUTPUT_PER_1K)

    def _priority_order(self) -> List[str]:
        candidates = [
            item["id"]
            for item in self.list_providers(include_hidden=False)
        ]
        return candidates

    def _cheapest_order(self) -> List[str]:
        from ..routing.router import cost_router

        candidates = self._priority_order()
        provider_costs = {provider_id: self._provider_costs(provider_id) for provider_id in candidates}
        return cost_router.rank(candidates, provider_costs)

    def _hybrid_order(self) -> List[str]:
        from ..routing.router import hybrid_router

        candidates = self._priority_order()
        provider_costs = {
            provider_id: self._provider_costs(provider_id)
            for provider_id in candidates
        }
        return hybrid_router.rank(candidates, provider_costs)

    def _local_order(self) -> List[str]:
        providers = self.list_providers(include_hidden=False)
        candidates = [
            item["id"]
            for item in providers
            if item["local_routing"] or item["tier"] == "self_hosted"
        ]
        return candidates

    def top_providers_for(
        self,
        capability: str,
        *,
        prefer_local: bool = False,
        prefer_cost: bool = False,
        limit: int = 6,
    ) -> List[str]:
        capability_normalized = capability.strip().lower()
        providers = self.list_providers(include_hidden=False)
        candidates = [
            item["id"]
            for item in providers
            if capability_normalized in {cap.lower() for cap in item["capabilities"]}
            and self.is_configured(item["id"])
        ]
        if prefer_local:
            local_candidates = [provider_id for provider_id in self._local_order() if provider_id in candidates]
            candidates = local_candidates
        elif prefer_cost:
            ranked = self._cheapest_order()
            candidates = [provider_id for provider_id in ranked if provider_id in candidates]

        return candidates[: max(1, limit)]

    def _resolve_model_alias(
        self,
        provider_id: Optional[str],
        model: Optional[str],
    ) -> tuple[Optional[str], Optional[str]]:
        if model is None:
            return provider_id, model
        alias = _MODEL_ALIASES.get(model)
        if alias is None:
            return provider_id, model
        alias_provider, alias_model = alias
        if provider_id in (None, "auto"):
            return alias_provider, alias_model
        canonical_id = canonical_provider_id(provider_id)
        if canonical_id == alias_provider:
            return canonical_id, alias_model
        return canonical_id or provider_id, model

    def _candidate_order(self, provider_id: Optional[str]) -> List[str]:
        if provider_id in (None, "auto"):
            return self._hybrid_order()
        if provider_id == "cheapest":
            return self._cheapest_order()
        if provider_id == "local":
            return self._local_order()

        canonical_id = canonical_provider_id(provider_id)
        if canonical_id and canonical_id in self._providers:
            return [canonical_id]
        return []

    async def check_provider(self, provider_id: str) -> Dict[str, Any]:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        config = self._configs.get(canonical_id, {})
        provider = self._providers.get(canonical_id)
        if not config or provider is None:
            return {
                "id": canonical_id,
                "configured": False,
                "healthy": False,
                "health": "unknown",
                "health_reason": "Unknown provider",
                "is_selectable": False,
                "latency_ms": 0.0,
            }

        configured = self.is_configured(canonical_id)
        if not configured:
            return {
                "id": canonical_id,
                "configured": False,
                "healthy": False,
                "health": "unknown",
                "health_reason": "Provider not configured",
                "is_selectable": False,
                "latency_ms": 0.0,
            }

        try:
            health = await provider.health_check()
            health_state = "healthy" if health.healthy else "unhealthy"
            return {
                "id": canonical_id,
                "configured": True,
                "healthy": health.healthy,
                "health": health_state,
                "health_reason": health.error,
                "is_selectable": bool(health.healthy),
                "latency_ms": round(float(health.latency_ms), 1),
            }
        except Exception as exc:
            return {
                "id": canonical_id,
                "configured": True,
                "healthy": False,
                "health": "unhealthy",
                "health_reason": str(exc),
                "is_selectable": False,
                "latency_ms": 0.0,
            }

    async def get_provider_inventory(
        self,
        include_hidden: bool = False,
    ) -> List[Dict[str, Any]]:
        providers = self.list_providers(include_hidden=include_hidden)
        checks = await asyncio.gather(
            *(self.check_provider(item["id"]) for item in providers),
            return_exceptions=True,
        )
        inventory: List[Dict[str, Any]] = []
        for provider_meta, health_meta in zip(providers, checks):
            if isinstance(health_meta, Exception):
                health_info = {
                    "configured": False,
                    "healthy": False,
                    "health": "unknown",
                    "health_reason": str(health_meta),
                    "is_selectable": False,
                    "latency_ms": 0.0,
                }
            else:
                health_info = health_meta
            inventory.append({**provider_meta, **health_info})
        return inventory

    async def health_all(self, include_hidden: bool = False) -> Dict[str, Any]:
        inventory = await self.get_provider_inventory(include_hidden=include_hidden)
        return {
            item["id"]: {
                "healthy": bool(item["healthy"]),
                "configured": bool(item["configured"]),
                "health": item["health"],
                "latency_ms": item["latency_ms"],
                "error": item["health_reason"],
                "is_selectable": bool(item["is_selectable"]),
            }
            for item in inventory
        }

    async def _stream_wrap(
        self,
        provider_id: str,
        provider: BaseProvider,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> ProviderResult:
        from ..routing.router import registry

        started_at = asyncio.get_running_loop().time()
        try:
            generator = provider.stream(messages, model, **kwargs)
            first_chunk = None
            async for chunk in generator:
                first_chunk = chunk
                break

            async def combined() -> AsyncGenerator[Dict[str, Any], None]:
                if first_chunk is not None:
                    yield first_chunk
                async for item in generator:
                    yield item

            latency = (asyncio.get_running_loop().time() - started_at) * 1000
            provider.record_success()
            registry.record_success(provider_id, latency_ms=latency, cost_usd=0.0)
            return ProviderResult(
                ok=True,
                provider=provider_id,
                model=model,
                latency_ms=latency,
                raw={"stream_gen": combined()},
            )
        except Exception as exc:
            provider.record_failure(str(exc))
            registry.record_failure(provider_id)
            return ProviderResult(
                ok=False,
                provider=provider_id,
                model=model,
                error=str(exc),
            )

    async def dispatch(
        self,
        pid: Optional[str],
        model: Optional[str],
        payload: Dict[str, Any],
        *,
        timeout_ms: int = 30_000,
        stream: bool = False,
    ) -> Dict[str, Any]:
        from ..routing.router import registry

        resolved_pid, resolved_model = self._resolve_model_alias(pid, model)
        messages = payload.get("messages", [])
        prompt = payload.get("prompt", "")
        candidates = self._candidate_order(resolved_pid)
        if not candidates:
            return {"ok": False, "error": f"unknown-provider:{pid}", "latency_ms": 0.0}

        explicit_mode = resolved_pid not in (None, "auto", "cheapest", "local")
        if explicit_mode:
            ordered = candidates
        else:
            configured_candidates = [
                provider_id for provider_id in candidates if self.is_configured(provider_id)
            ]
            available = [
                provider_id
                for provider_id in configured_candidates
                if self._providers[provider_id].is_available()
                and registry.get(provider_id).success_rate >= self._routing_min_success_rate
            ]
            ordered = available or configured_candidates

        if explicit_mode and not ordered:
            ordered = candidates

        if not ordered:
            return {"ok": False, "error": "no-configured-providers", "latency_ms": 0.0}

        last_error = "all providers failed"
        for provider_id in ordered:
            provider = self._providers[provider_id]
            model_name = resolved_model or provider.default_model
            kwargs = dict(payload)
            kwargs.pop("messages", None)
            kwargs.pop("prompt", None)
            kwargs.pop("model", None)
            try:
                if stream:
                    result = await asyncio.wait_for(
                        self._stream_wrap(
                            provider_id,
                            provider,
                            messages,
                            model_name,
                            prompt=prompt,
                            **kwargs,
                        ),
                        timeout=timeout_ms / 1000,
                    )
                    if result.ok:
                        return {
                            "ok": True,
                            "stream": result.raw.get("stream_gen"),
                            "provider": provider_id,
                            "model": model_name,
                        }
                    last_error = result.error or last_error
                    continue

                result = await asyncio.wait_for(
                    provider.invoke(
                        messages,
                        model_name,
                        stream=False,
                        prompt=prompt,
                        **kwargs,
                    ),
                    timeout=timeout_ms / 1000,
                )
                if result.ok:
                    provider.record_success()
                    registry.record_success(
                        provider_id,
                        latency_ms=float(result.latency_ms),
                        cost_usd=float(result.cost_usd or 0.0),
                    )
                    return result.to_dict()

                last_error = result.error or last_error
                provider.record_failure(last_error)
                registry.record_failure(provider_id)
            except asyncio.TimeoutError:
                last_error = f"timeout after {timeout_ms}ms"
                provider.record_failure(last_error)
                registry.record_failure(provider_id)
            except Exception as exc:
                last_error = str(exc)
                provider.record_failure(last_error)
                registry.record_failure(provider_id)

        return {
            "ok": False,
            "error": last_error,
            "provider": "none",
            "latency_ms": 0.0,
        }

    async def invoke_provider(
        self,
        provider_id: Optional[str] = None,
        model: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        timeout_ms: int = 30_000,
        stream: bool = False,
        pid: Optional[str] = None,
    ) -> Dict[str, Any]:
        selected_provider = pid if pid is not None else provider_id
        return await self.dispatch(
            pid=selected_provider,
            model=model,
            payload=payload or {},
            timeout_ms=timeout_ms,
            stream=stream,
        )


dispatcher = ProviderDispatcher()


async def invoke_provider(
    pid: Optional[str],
    model: Optional[str],
    payload: Dict[str, Any],
    timeout_ms: int = 30_000,
    stream: bool = False,
) -> Dict[str, Any]:
    return await dispatcher.dispatch(
        pid=pid,
        model=model,
        payload=payload,
        timeout_ms=timeout_ms,
        stream=stream,
    )


async def get_provider_health(include_hidden: bool = False) -> Dict[str, Any]:
    return await dispatcher.health_all(include_hidden=include_hidden)


def list_providers(include_hidden: bool = False) -> List[Dict[str, Any]]:
    return dispatcher.list_providers(include_hidden=include_hidden)
