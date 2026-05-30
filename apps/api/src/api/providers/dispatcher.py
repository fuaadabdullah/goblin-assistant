"""
Authoritative provider dispatcher for Goblin Assistant.

Config is loaded from config/providers.toml — the SINGLE source of truth.
The shared Pydantic schema in packages/shared/src/provider_config.py is used
for validation at CI/build time; this module parses TOML directly at runtime.
"""

from __future__ import annotations

import asyncio
import importlib
import os
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

import structlog

from .aliyun_provider import AliyunProvider
from .anthropic_provider import AnthropicProvider
from .azure_provider import AzureOpenAIProvider
from .base import (
    BaseProvider,
    ProviderResult,
    classify_provider_error,
    ProviderErrorCategory,
)
from .contracts import ProviderAdapter
from .llamacpp_provider import LlamaCPPProvider
from .mock_provider import MockProvider
from .ollama_provider import OllamaProvider
from .openai_compatible import OpenAICompatibleProvider
from .openai_provider import OpenAIProvider
from .siliconeflow import SiliconeFlowProvider
from .vertex_provider import VertexAIProvider

logger = structlog.get_logger(__name__)

try:
    from dotenv import load_dotenv

    load_dotenv()
    load_dotenv(".env.local")
except ImportError:
    pass

_PROVIDER_CLASS_MAP: Dict[str, type[BaseProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "groq": OpenAICompatibleProvider,
    "siliconeflow": SiliconeFlowProvider,
    "deepseek": OpenAICompatibleProvider,
    "gemini": OpenAICompatibleProvider,
    "azure_openai": AzureOpenAIProvider,
    "vertex_ai": VertexAIProvider,
    "aliyun": AliyunProvider,
    "together": OpenAICompatibleProvider,
    "replicate": OpenAICompatibleProvider,
    "huggingface": OpenAICompatibleProvider,
    "cohere": OpenAICompatibleProvider,
    "ollama_gcp": OllamaProvider,
    "ollama_local": OllamaProvider,
    "llamacpp_gcp": LlamaCPPProvider,
    "mock": MockProvider,
}

# ── TOML loader (runtime) ─────────────────────────────────────────────────


def _parse_toml(path: Path) -> dict:
    try:
        import tomllib

        with open(path, "rb") as f:
            return tomllib.load(f)
    except ImportError:
        toml = importlib.import_module("toml")
        with open(path, "r", encoding="utf-8") as f:
            return toml.load(f)


def _load_toml_providers() -> dict:
    """Load provider configs from config/providers.toml. Returns {id: {config}}."""
    config_path = Path(__file__).resolve().parents[5] / "config" / "providers.toml"
    if not config_path.exists():
        logger.warning("provider_toml_not_found", path=str(config_path))
        return {}

    try:
        parsed = _parse_toml(config_path)
    except (OSError, ValueError) as exc:
        logger.warning("provider_toml_load_failed", error=str(exc))
        return {}

    providers_raw = parsed.get("providers", {})
    if not isinstance(providers_raw, dict):
        return {}

    # Apply env-var endpoint overrides
    result: dict = {}
    for pid, raw in providers_raw.items():
        if not isinstance(raw, dict):
            continue
        resolved = dict(raw)
        endpoint_env = str(resolved.get("endpoint_env", "")).strip()
        fallback_env = f"PROVIDER_{pid.upper()}_ENDPOINT"
        env_endpoint = os.getenv(endpoint_env, "").strip() if endpoint_env else ""
        if not env_endpoint:
            env_endpoint = os.getenv(fallback_env, "").strip()
        if env_endpoint:
            resolved["endpoint"] = env_endpoint
        resolved["provider_id"] = pid
        result[pid] = resolved

    return result


def _load_aliases(parsed: dict) -> Dict[str, str]:
    aliases = parsed.get("provider_aliases", {})
    return dict(aliases) if isinstance(aliases, dict) else {}


def _load_model_aliases(parsed: dict) -> Dict[str, tuple[str, str]]:
    """Load model aliases from TOML. Returns {alias: (provider, model)}."""
    raw = parsed.get("model_aliases", {})
    if not isinstance(raw, dict):
        return {}
    result: Dict[str, tuple[str, str]] = {}
    for alias, val in raw.items():
        if isinstance(val, dict):
            prov = val.get("provider", "")
            model = val.get("model", "")
            if prov and model:
                result[alias] = (prov, model)
    return result


# ── Load once ─────────────────────────────────────────────────────────────

_toml_path = Path(__file__).resolve().parents[5] / "config" / "providers.toml"
_toml_data = _parse_toml(_toml_path) if _toml_path.exists() else {}
_PROVIDER_CONFIGS: Dict[str, Dict[str, Any]] = _load_toml_providers()
_PROVIDER_ALIASES: Dict[str, str] = _load_aliases(_toml_data)
_MODEL_ALIASES: Dict[str, tuple[str, str]] = _load_model_aliases(_toml_data)


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
        self._configs: Dict[str, Dict[str, Any]] = _PROVIDER_CONFIGS
        self._providers: Dict[str, ProviderAdapter] = {}
        self._routing_min_success_rate = self._load_min_success_rate()
        self._build_registry()
        self._startup_preflight()

    def _startup_preflight(self) -> None:
        configured = []
        unconfigured = []
        for pid in self._configs:
            if pid == "mock":
                continue
            if self.is_configured(pid):
                configured.append(pid)
            else:
                unconfigured.append(pid)
        logger.info(
            "provider_preflight",
            configured=configured,
            configured_count=len(configured),
            unconfigured=unconfigured,
            unconfigured_count=len(unconfigured),
            total=len(configured) + len(unconfigured),
        )
        if not configured:
            logger.warning(
                "no_providers_configured",
                hint="Set API key env vars for at least one provider",
            )

    def _load_min_success_rate(self) -> float:
        raw_value = os.getenv("ROUTING_MIN_SUCCESS_RATE", "0.3").strip()
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            return 0.3
        return max(0.0, min(1.0, value))

    def _build_registry(self) -> None:
        for provider_id, config in self._configs.items():
            provider_class = _PROVIDER_CLASS_MAP.get(provider_id)
            if provider_class is None:
                logger.warning("no_class_for_provider", provider=provider_id)
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
            has_project = bool(
                os.getenv("VERTEX_AI_PROJECT", "").strip()
                or os.getenv("GCP_PROJECT_ID", "").strip()
                or config.get("project_env")
                and os.getenv(str(config["project_env"]), "").strip()
            )
            if not has_project:
                return False
            has_creds = bool(
                os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
                or os.getenv("VERTEX_AI_SERVICE_ACCOUNT_JSON", "").strip()
                or os.getenv("GCP_SERVICE_ACCOUNT_KEY", "").strip()
            )
            return has_creds
        if provider_id == "azure_openai":
            api_key_env = str(config.get("api_key_env", "AZURE_API_KEY"))
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", config.get("endpoint", "")).strip()
            deployment = os.getenv(
                "AZURE_DEPLOYMENT_ID",
                str(config.get("default_deployment") or config.get("default_model", "")),
            ).strip()
            return bool(os.getenv(api_key_env, "").strip() and endpoint and deployment)
        endpoint_env = config.get("endpoint_env", "")
        if config.get("selectable_requires_env"):
            return bool(endpoint_env and os.getenv(str(endpoint_env), "").strip())
        api_key_env = config.get("api_key_env", "")
        if api_key_env:
            return bool(os.getenv(str(api_key_env), "").strip())
        if self._is_self_hosted(config):
            return bool(endpoint_env and os.getenv(str(endpoint_env), "").strip())
        return bool(str(config.get("endpoint", "")).strip())

    def get_provider(self, provider_id: str) -> ProviderAdapter:
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
        return [item["id"] for item in self.list_providers(include_hidden=False)]

    def _cheapest_order(self) -> List[str]:
        from ..routing.router import cost_router

        candidates = self._priority_order()
        provider_costs = {p: self._provider_costs(p) for p in candidates}
        return cost_router.rank(candidates, provider_costs)

    def _hybrid_order(self) -> List[str]:
        from ..routing.router import hybrid_router

        candidates = self._priority_order()
        provider_costs = {p: self._provider_costs(p) for p in candidates}
        return hybrid_router.rank(candidates, provider_costs)

    def _local_order(self) -> List[str]:
        providers = self.list_providers(include_hidden=False)
        return [
            item["id"]
            for item in providers
            if item["local_routing"] or item["tier"] == "self_hosted"
        ]

    def _allow_self_hosted_auto_routing(self) -> bool:
        return os.getenv("ENABLE_SELF_HOSTED_AUTO_ROUTING", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def _is_auto_routing_candidate(self, provider_id: str) -> bool:
        config = self._configs.get(provider_id, {})
        if not config:
            return False
        if config.get("local_routing") or self._is_self_hosted(config):
            return self._allow_self_hosted_auto_routing()
        return True

    def _auto_configured_candidates(self, candidates: List[str]) -> List[str]:
        configured = [p for p in candidates if self.is_configured(p)]
        filtered = [p for p in configured if self._is_auto_routing_candidate(p)]
        if filtered:
            configured = filtered
        try:
            from ..services.provider_health import health_monitor

            healthy = [p for p in configured if health_monitor.is_available(p)]
            if healthy:
                return healthy
        except Exception:
            logger.debug("provider_health_filter_unavailable")
        return configured

    def top_providers_for(
        self,
        capability: str,
        *,
        prefer_local: bool = False,
        prefer_cost: bool = False,
        limit: int = 6,
    ) -> List[str]:
        cap = capability.strip().lower()
        providers = self.list_providers(include_hidden=False)
        candidates = [
            item["id"]
            for item in providers
            if cap in {c.lower() for c in item["capabilities"]} and self.is_configured(item["id"])
        ]
        if prefer_local:
            local_candidates = [p for p in self._local_order() if p in candidates]
            candidates = local_candidates
        elif prefer_cost:
            ranked = self._cheapest_order()
            candidates = [p for p in ranked if p in candidates]
        return candidates[: max(1, limit)]

    def _resolve_model_alias(
        self, provider_id: Optional[str], model: Optional[str]
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
            billing = getattr(health, "billing_issue", False)
            if health.healthy:
                health_state = "healthy"
            elif billing:
                health_state = "billing_issue"
            else:
                health_state = "unhealthy"
            return {
                "id": canonical_id,
                "configured": True,
                "healthy": health.healthy,
                "health": health_state,
                "health_reason": health.error,
                "billing_issue": billing,
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
                "billing_issue": False,
                "is_selectable": False,
                "latency_ms": 0.0,
            }

    async def get_provider_inventory(self, include_hidden: bool = False) -> List[Dict[str, Any]]:
        providers = self.list_providers(include_hidden=include_hidden)
        checks = await asyncio.gather(
            *(self.check_provider(item["id"]) for item in providers),
            return_exceptions=True,
        )
        inventory: List[Dict[str, Any]] = []
        for meta, health in zip(providers, checks):
            if isinstance(health, Exception):
                health = {
                    "configured": False,
                    "healthy": False,
                    "health": "unknown",
                    "health_reason": str(health),
                    "is_selectable": False,
                    "latency_ms": 0.0,
                }
            inventory.append({**meta, **health})
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
            gen = provider.stream(messages, model, **kwargs)
            first = None
            async for chunk in gen:
                first = chunk
                break

            async def combined() -> AsyncGenerator[Dict[str, Any], None]:
                if first is not None:
                    yield first
                async for item in gen:
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
                error_category=classify_provider_error(exc).value,
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
            configured_candidates = self._auto_configured_candidates(candidates)
            if not configured_candidates:
                configured_candidates = [p for p in candidates if self.is_configured(p)]
            available = [
                p
                for p in configured_candidates
                if self._providers[p].is_available()
                and registry.get(p).success_rate >= self._routing_min_success_rate
            ]
            ordered = available or configured_candidates
        if explicit_mode and not ordered:
            ordered = candidates
        if not ordered:
            return {"ok": False, "error": "no-configured-providers", "latency_ms": 0.0}

        last_error = "all providers failed"
        last_category: Optional[ProviderErrorCategory] = None
        for provider_id in ordered:
            provider = self._providers[provider_id]
            model_name = resolved_model or provider.default_model
            kwargs = dict(payload)
            for k in ("messages", "prompt", "model"):
                kwargs.pop(k, None)
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
                    provider.invoke(messages, model_name, stream=False, prompt=prompt, **kwargs),
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
                last_category = classify_provider_error(last_error)
                provider.record_failure(last_error)
                registry.record_failure(provider_id)
            except asyncio.TimeoutError:
                last_error = f"timeout after {timeout_ms}ms"
                last_category = ProviderErrorCategory.TIMEOUT
                provider.record_failure(last_error)
                registry.record_failure(provider_id)
            except Exception as exc:
                last_error = str(exc)
                last_category = classify_provider_error(exc)
                provider.record_failure(last_error)
                registry.record_failure(provider_id)
        return {
            "ok": False,
            "error": last_error,
            "error_category": last_category.value if last_category else None,
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
        return await self.dispatch(
            pid=pid or provider_id,
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
        pid=pid, model=model, payload=payload, timeout_ms=timeout_ms, stream=stream
    )


async def get_provider_health(include_hidden: bool = False) -> Dict[str, Any]:
    return await dispatcher.health_all(include_hidden=include_hidden)


def list_providers(include_hidden: bool = False) -> List[Dict[str, Any]]:
    return dispatcher.list_providers(include_hidden=include_hidden)
