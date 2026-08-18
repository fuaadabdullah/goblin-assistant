"""
Authoritative provider dispatcher for Goblin Assistant.

Config is loaded from config/providers.toml — the SINGLE source of truth.
The shared Pydantic schema in packages/shared/src/provider_config.py is used
for validation at CI/build time; this module parses TOML directly at runtime.
"""

from __future__ import annotations

import asyncio
import importlib
import re
import os
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

import structlog

from .aliyun_provider import AliyunProvider
from .anthropic_provider import AnthropicProvider
from .azure_provider import AzureOpenAIProvider
from .base import BaseProvider, ProviderResult, classify_provider_error, ProviderErrorCategory
from .google_cloud_selfhosted_provider import GoogleCloudSelfhostedProvider
from .llamacpp_provider import LlamaCPPProvider
from .mock_provider import MockProvider
from .ollama_provider import OllamaProvider
from .openai_compatible import OpenAICompatibleProvider
from .openai_provider import OpenAIProvider
from .siliconeflow import SiliconeFlowProvider
from .vertex_provider import VertexAIProvider
from .dispatcher_pkg.sanitization import sanitize_error_message, known_secrets
from .dispatcher_pkg.test_mode import (
    invoke_with_test_mode,
    maybe_inject_test_failure,
    active_test_mode_state,
    test_mode_context,
)

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
    "gcp_vm": GoogleCloudSelfhostedProvider,
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


def _load_provider_toml(log=None) -> dict:
    """Load and return the raw TOML data from config/providers.toml."""
    config_path = Path(__file__).resolve().parents[5] / "config" / "providers.toml"
    if not config_path.exists():
        (log or logger).warning("provider_toml_not_found", path=str(config_path))
        return {}
    try:
        return _parse_toml(config_path)
    except (OSError, ValueError) as exc:
        (log or logger).warning("provider_toml_load_failed", error=str(exc))
        return {}


def _load_toml_providers(toml: dict = None, log=None) -> dict:
    """Extract provider configs from raw TOML data. Returns {id: {config}}."""
    if toml is None:
        toml = _load_provider_toml(log)
    providers_raw = toml.get("providers", {})
    if not isinstance(providers_raw, dict):
        return {}
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


def _load_model_aliases(parsed: dict) -> Tuple[Dict[str, tuple], List[tuple]]:
    """Load model aliases from TOML. Returns (exact_aliases, pattern_aliases)."""
    raw = parsed.get("model_aliases", {})
    if not isinstance(raw, dict):
        return {}, []
    exact: Dict[str, tuple] = {}
    patterns: List[tuple] = []
    for alias, val in raw.items():
        if isinstance(val, dict):
            prov = val.get("provider", "")
            model = val.get("model", "")
            if prov and model:
                if "*" in alias or "?" in alias or re.search(r"\(.*\)", alias):
                    try:
                        pat = re.compile(alias)
                        patterns.append((pat, prov, model))
                    except re.error:
                        exact[alias] = (prov, model)
                else:
                    exact[alias] = (prov, model)
    return exact, patterns


def _load_visible_providers(parsed: dict) -> List[str]:
    raw = parsed.get("visible_providers", [])
    return list(raw) if isinstance(raw, list) else []


def validate_model_alias_targets(
    aliases: Dict[str, tuple],
    configs: Dict[str, Any],
    log=None,
) -> None:
    pass


def reload_provider_catalog() -> None:
    global _provider_toml, _PROVIDER_CONFIGS, _PROVIDER_ALIASES, _MODEL_ALIASES, _MODEL_ALIAS_PATTERNS, _VISIBLE_PROVIDER_IDS
    _provider_toml = _load_provider_toml(logger)
    _PROVIDER_CONFIGS = _load_toml_providers(_provider_toml, logger)
    _PROVIDER_ALIASES = _load_aliases(_provider_toml)
    _MODEL_ALIASES, _MODEL_ALIAS_PATTERNS = _load_model_aliases(_provider_toml)
    _VISIBLE_PROVIDER_IDS = _load_visible_providers(_provider_toml)
    validate_model_alias_targets(_MODEL_ALIASES, _PROVIDER_CONFIGS, logger)
    dispatcher.apply_reloaded_catalog(
        configs=_PROVIDER_CONFIGS,
        aliases=_PROVIDER_ALIASES,
        model_aliases=_MODEL_ALIASES,
    )


# ── Load once ─────────────────────────────────────────────────────────────

_toml_path = Path(__file__).resolve().parents[5] / "config" / "providers.toml"
_provider_toml: dict = _parse_toml(_toml_path) if _toml_path.exists() else {}
_PROVIDER_CONFIGS: Dict[str, Dict[str, Any]] = _load_toml_providers(_provider_toml)
_PROVIDER_ALIASES: Dict[str, str] = _load_aliases(_provider_toml)
_MODEL_ALIASES: Dict[str, tuple] = {}
_MODEL_ALIAS_PATTERNS: List[tuple] = []
_MODEL_ALIASES, _MODEL_ALIAS_PATTERNS = _load_model_aliases(_provider_toml)
_VISIBLE_PROVIDER_IDS: List[str] = _load_visible_providers(_provider_toml)


def _normalize_token(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def canonical_provider_id(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = _normalize_token(value)
    if not normalized:
        return None
    return _PROVIDER_ALIASES.get(normalized, normalized)


class _NullRegistry:
    def runtime_config(self, *args: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        return None


class ProviderDispatcher:
    def __init__(
        self,
        configs: Optional[Dict[str, Dict[str, Any]]] = None,
        class_map: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._configs: Dict[str, Dict[str, Any]] = configs if configs is not None else _PROVIDER_CONFIGS
        self._class_map_override = class_map
        self._providers: Dict[str, BaseProvider] = {}
        self._provider_list_cache: Dict[str, Any] = {}
        self._warmup_states: Dict[str, Any] = {}
        self._background_started: bool = False
        self._circuit_canary_percent: float = 0.05
        self._routing_min_success_rate = self._load_min_success_rate()
        self._test_mode_stack: List[Dict[str, Any]] = []
        from .provider_registry import ProviderRegistry
        try:
            self._registry = ProviderRegistry()
        except Exception:
            self._registry = _NullRegistry()
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

    def _runtime_config(self, provider_id: str) -> Optional[Dict[str, Any]]:
        raw = self._configs.get(provider_id)
        if not isinstance(raw, dict):
            return None
        try:
            canonical = canonical_provider_id(provider_id) or provider_id
            return self._registry.runtime_config(canonical, raw)
        except Exception as exc:
            logger.warning("runtime_config_failed", provider=provider_id, error=str(exc))
            return None

    def update_backend_endpoint(self, provider_id: str, engine: str, url: str) -> None:
        config = self._configs.get(provider_id, {})
        if not isinstance(config, dict):
            return
        for backend in config.get("backends", []):
            if isinstance(backend, dict) and backend.get("engine") == engine:
                backend["endpoint"] = url
                env_key = backend.get("endpoint_env", "")
                if env_key:
                    os.environ[env_key] = url
                break

    def update_provider_endpoint(self, provider_id: str, url: str) -> None:
        if provider_id not in self._configs:
            raise KeyError(f"Unknown provider: {provider_id}")
        config = self._configs[provider_id]
        if not isinstance(config, dict):
            return
        config["endpoint"] = url
        self._provider_list_cache.clear()
        env_key = str(config.get("endpoint_env", "")).strip()
        if env_key:
            os.environ[env_key] = url

    def apply_reloaded_catalog(
        self,
        configs: Dict[str, Dict[str, Any]],
        aliases: Dict[str, str],
        model_aliases: Dict[str, tuple],
    ) -> None:
        self._configs = configs
        self._providers = {}
        self._provider_list_cache = {}
        self._warmup_states = {}
        self._build_registry()

    def start_background_tasks(self) -> None:
        if self._background_started:
            return
        self._background_started = True
        from .dispatcher_pkg.warmup import (
            _load_prewarm_enabled,
            _load_prewarm_latency_threshold_ms,
            _prewarm_self_hosted_providers,
        )
        if not _load_prewarm_enabled():
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                _prewarm_self_hosted_providers(
                    self._warmup_states,
                    self._configs,
                    self._get_or_create_provider,
                    self.is_configured,
                    lambda e: str(e),
                    logger=logger,
                    prewarm_latency_threshold_ms=_load_prewarm_latency_threshold_ms(),
                )
            )
        except RuntimeError:
            pass

    def reload_config(self) -> None:
        reload_provider_catalog()
        self.start_background_tasks()

    def test_mode(self, profiles: Dict[str, Dict[str, Any]]):
        return test_mode_context(
            self._test_mode_stack,
            profiles,
            self,
            canonical_provider_id_fn=lambda pid: canonical_provider_id(pid) or pid,
        )

    def _ensure_provider(self, provider_id: str) -> Optional[BaseProvider]:
        return self._get_or_create_provider(provider_id)

    def _sanitize_error(self, exc: Exception) -> str:
        return sanitize_error_message(str(exc), known_secrets(self._configs))

    def _provider_error_category(self, value: Any, fallback: str) -> Optional[ProviderErrorCategory]:
        if value is None:
            return classify_provider_error(fallback) if fallback else None
        if isinstance(value, ProviderErrorCategory):
            return value
        try:
            return ProviderErrorCategory(str(value).strip().lower().replace("_", "-"))
        except Exception:
            return classify_provider_error(fallback) if fallback else None

    def record_routing_outcome(
        self, provider_id: str, ok: bool, latency_ms: float = 0.0, cost_usd: float = 0.0
    ) -> None:
        from ..routing.router import registry
        if ok:
            registry.record_success(provider_id, latency_ms=latency_ms, cost_usd=cost_usd)
        else:
            registry.record_failure(provider_id)

    def note_provider_result(
        self, provider_id: str, ok: bool, latency_ms: float = 0.0, error: str = ""
    ) -> None:
        from .dispatcher_pkg.warmup import note_provider_result, _load_prewarm_latency_threshold_ms
        note_provider_result(
            self._warmup_states,
            provider_id,
            ok=ok,
            latency_ms=latency_ms,
            error=error,
            prewarm_latency_threshold_ms=_load_prewarm_latency_threshold_ms(),
        )

    def _is_warmup_routing_blocked(self, provider_id: str) -> bool:
        from .dispatcher_pkg.warmup import is_warmup_routing_blocked
        return is_warmup_routing_blocked(self._warmup_states, self._configs, provider_id)

    def _is_canary_attempt(self, provider_id: str, model: Optional[str] = None) -> bool:
        _ = model
        provider = self._get_or_create_provider(provider_id)
        if provider is None:
            return False
        return provider.soft_open_probe_available()

    def _build_invoke_kwargs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        kwargs = dict(payload)
        for key in ("messages", "prompt", "model", "user_id", "request_id", "intent"):
            kwargs.pop(key, None)
        return kwargs

    async def _invoke_with_test_mode(
        self,
        provider_id: str,
        provider: BaseProvider,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> ProviderResult:
        def _cat_fn(cat_str: Any, fallback: str) -> ProviderErrorCategory:
            try:
                if cat_str:
                    return ProviderErrorCategory(str(cat_str).replace("_", "-"))
            except ValueError:
                pass
            return classify_provider_error(fallback)

        return await invoke_with_test_mode(
            self._test_mode_stack,
            provider_id,
            provider,
            messages,
            model,
            sanitize_error_fn=lambda e: sanitize_error_message(e, known_secrets(self._configs)),
            provider_error_category_fn=_cat_fn,
            **kwargs,
        )

    async def _apply_test_mode_delay(self, provider_id: str) -> None:
        from .dispatcher_pkg.test_mode import apply_test_mode_delay
        await apply_test_mode_delay(self._test_mode_stack, provider_id)

    async def _maybe_inject_test_failure(
        self, provider_id: str, model: str
    ) -> Optional[ProviderResult]:
        def _cat_fn(cat_str: Any, fallback: str) -> ProviderErrorCategory:
            try:
                if cat_str:
                    return ProviderErrorCategory(str(cat_str).replace("_", "-"))
            except ValueError:
                pass
            return classify_provider_error(fallback)

        return await maybe_inject_test_failure(
            self._test_mode_stack,
            provider_id,
            model,
            provider_error_category_fn=_cat_fn,
        )

    def _warmup_state_for(self, provider_id: str) -> Dict[str, Any]:
        return self._warmup_states.get(provider_id, {"state": "idle"})

    def debug_info(self) -> Dict[str, Any]:
        from ..routing.router import registry
        routing_table = []
        for item in self.list_providers(include_hidden=True):
            pid = item["id"]
            config = self._configs.get(pid, {})
            routing_table.append({
                **item,
                "provider_id": pid,
                "capabilities": list(config.get("capabilities", [])) if isinstance(config, dict) else [],
                "configured": self.is_configured(pid),
                "warmup": self._warmup_state_for(pid),
                "budget_status": self._budget_status(),
            })
        try:
            registry_stats = registry.snapshot()
        except Exception:
            registry_stats = {}
        try:
            metrics = registry.metrics_snapshot()
        except Exception:
            metrics = {}
        try:
            persisted = registry.persisted_snapshot()
        except Exception:
            persisted = {}
        try:
            persistence = registry.persistence_status()
        except Exception:
            persistence = {}
        return {
            "routing_table": routing_table,
            "registry_stats": registry_stats,
            "metrics": metrics,
            "persisted": persisted,
            "persistence": persistence,
            "circuit_canary_percent": self._circuit_canary_percent,
            "budget": self._budget_status(),
            "routing_min_success_rate": self._routing_min_success_rate,
            "model_aliases": dict(_MODEL_ALIASES),
            "provider_aliases": dict(_PROVIDER_ALIASES),
            "visible_provider_order": list(_VISIBLE_PROVIDER_IDS),
        }

    def _load_min_success_rate(self) -> float:
        raw_value = os.getenv("ROUTING_MIN_SUCCESS_RATE", "0.3").strip()
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            return 0.3
        return max(0.0, min(1.0, value))

    def _build_registry(self) -> None:
        # Providers are instantiated lazily on first access via get_provider().
        pass

    def _get_or_create_provider(self, provider_id: str) -> Optional[BaseProvider]:
        if provider_id in self._providers:
            return self._providers[provider_id]
        config = self._configs.get(provider_id)
        if config is None or not isinstance(config, dict):
            return None
        class_map = self._class_map_override if self._class_map_override is not None else _PROVIDER_CLASS_MAP
        provider_class = class_map.get(provider_id)
        if provider_class is None:
            logger.warning("no_class_for_provider", provider=provider_id)
            return None
        try:
            provider = provider_class(provider_id, config)
            self._providers[provider_id] = provider
            return provider
        except Exception as exc:
            logger.warning("provider_init_failed", provider=provider_id, error=str(exc))
            return None

    def _build_provider_list(self, include_hidden: bool = False) -> List[Dict[str, Any]]:
        providers: List[Dict[str, Any]] = []
        for provider_id, config in self._configs.items():
            if not isinstance(config, dict):
                continue
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

    def list_providers(self, include_hidden: bool = False) -> List[Dict[str, Any]]:
        cache_key = f"include_hidden={include_hidden}"
        if cache_key in self._provider_list_cache:
            return self._provider_list_cache[cache_key]
        result = self._build_provider_list(include_hidden=include_hidden)
        self._provider_list_cache[cache_key] = result
        return result

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

    def get_provider(self, provider_id: str) -> BaseProvider:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        provider = self._get_or_create_provider(canonical_id)
        if provider is None:
            raise KeyError(f"Unknown provider: {provider_id}")
        return provider

    def get_provider_config(self, provider_id: str) -> Dict[str, Any]:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        return dict(self._configs.get(canonical_id, {}))

    def _provider_costs(self, provider_id: str) -> tuple[float, float]:
        provider = self._get_or_create_provider(provider_id)
        if provider is None:
            return (float("inf"), float("inf"))
        return (provider.COST_INPUT_PER_1K, provider.COST_OUTPUT_PER_1K)

    def _budget_status(self) -> Dict[str, Any]:
        return {
            "cap_usd": float(os.getenv("HOURLY_BUDGET_USD", "10.0")),
            "current_hour_spend_usd": 0.0,
            "current_hour_spend_by_provider": {},
            "over_budget": False,
        }

    def _apply_budget_rerank(self, candidates: List[str], routing_mode: str = "auto") -> List[str]:
        status = self._budget_status()
        if not status.get("over_budget"):
            return list(candidates)
        zero_cost = [p for p in candidates if sum(self._provider_costs(p)) == 0.0]
        non_zero = [p for p in candidates if p not in zero_cost]
        return zero_cost + non_zero

    def _priority_order(self) -> List[str]:
        return [
            item["id"]
            for item in self.list_providers(include_hidden=False)
        ]

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
            "1", "true", "yes", "on",
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
            item["id"] for item in providers
            if cap in {c.lower() for c in item["capabilities"]}
            and self.is_configured(item["id"])
        ]
        if prefer_local:
            local_candidates = [p for p in self._local_order() if p in candidates]
            candidates = local_candidates
        elif prefer_cost:
            ranked = self._cheapest_order()
            candidates = [p for p in ranked if p in candidates]
        return candidates[:max(1, limit)]

    def _resolve_pattern_model_alias(self, model: str) -> Optional[tuple]:
        for pat, alias_provider, alias_model_template in _MODEL_ALIAS_PATTERNS:
            m = pat.match(model)
            if m:
                resolved_model = alias_model_template
                for i, group in enumerate(m.groups(), 1):
                    resolved_model = resolved_model.replace(f"{{{i}}}", group)
                return (alias_provider, resolved_model)
        return None

    def _resolve_model_alias(
        self, provider_id: Optional[str], model: Optional[str]
    ) -> tuple[Optional[str], Optional[str]]:
        if model is None:
            return provider_id, model
        alias = _MODEL_ALIASES.get(model)
        if alias is not None:
            alias_provider, alias_model = alias
            if provider_id in (None, "auto"):
                return alias_provider, alias_model
            canonical_id = canonical_provider_id(provider_id)
            if canonical_id == alias_provider:
                return canonical_id, alias_model
            return canonical_id or provider_id, model
        pattern_result = self._resolve_pattern_model_alias(model)
        if pattern_result is not None:
            alias_provider, resolved_model = pattern_result
            if provider_id in (None, "auto"):
                return alias_provider, resolved_model
            canonical_id = canonical_provider_id(provider_id)
            if canonical_id == alias_provider:
                return canonical_id, resolved_model
            return canonical_id or provider_id, model
        return provider_id, model

    def _candidate_order(self, provider_id: Optional[str]) -> List[str]:
        if provider_id in (None, "auto"):
            return self._hybrid_order()
        if provider_id == "cheapest":
            return self._cheapest_order()
        if provider_id == "local":
            return self._local_order()
        canonical_id = canonical_provider_id(provider_id) or provider_id
        if canonical_id and (canonical_id in self._providers or canonical_id in self._configs):
            return [canonical_id]
        return []

    async def check_provider(self, provider_id: str) -> Dict[str, Any]:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        config = self._configs.get(canonical_id, {})
        provider = self._get_or_create_provider(canonical_id)
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
        # Test mode health override
        if self._test_mode_stack:
            tm_state = active_test_mode_state(self._test_mode_stack, canonical_id)
            if tm_state is not None:
                hc_override = tm_state["profiles"][canonical_id].get("health_check")
                if hc_override is not None:
                    billing = bool(hc_override.get("billing_issue", False))
                    healthy = bool(hc_override.get("healthy", False))
                    health_state = "billing_issue" if billing else ("healthy" if healthy else "unhealthy")
                    return {
                        "id": canonical_id,
                        "configured": True,
                        "healthy": healthy,
                        "health": health_state,
                        "health_reason": hc_override.get("error"),
                        "billing_issue": billing,
                        "is_selectable": healthy,
                        "latency_ms": float(hc_override.get("latency_ms", 0.0)),
                    }

        timeout_ms = float(config.get("health_check_timeout_ms", 5000))
        try:
            health = await asyncio.wait_for(provider.health_check(), timeout=timeout_ms / 1000)
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
        except asyncio.TimeoutError:
            return {
                "id": canonical_id,
                "configured": True,
                "healthy": False,
                "health": "unhealthy",
                "health_reason": f"health check timed out after {timeout_ms:.0f}ms",
                "billing_issue": False,
                "is_selectable": False,
                "latency_ms": 0.0,
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
                    "configured": False, "healthy": False, "health": "unknown",
                    "health_reason": str(health), "is_selectable": False, "latency_ms": 0.0,
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
        self, provider_id: str, provider: BaseProvider,
        messages: List[Dict[str, str]], model: str, **kwargs: Any,
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
                ok=True, provider=provider_id, model=model,
                latency_ms=latency, raw={"stream_gen": combined()},
            )
        except Exception as exc:
            provider.record_failure(str(exc))
            registry.record_failure(provider_id)
            return ProviderResult(
                ok=False, provider=provider_id, model=model, error=str(exc),
                error_category=classify_provider_error(exc).value,
            )

    async def dispatch(
        self, pid: Optional[str], model: Optional[str],
        payload: Dict[str, Any], *, timeout_ms: int = 30_000, stream: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        from ..routing.router import registry
        from .quota_service import quota_service
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
                p for p in configured_candidates
                if (prov := self._get_or_create_provider(p)) is not None
                and prov.is_available()
                and registry.get(p).success_rate >= self._routing_min_success_rate
            ]
            ordered = available or configured_candidates
        if explicit_mode and not ordered:
            ordered = candidates
        if not ordered:
            return {"ok": False, "error": "no-configured-providers", "latency_ms": 0.0}

        if dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "resolved_provider": ordered[0],
                "resolved_model": resolved_model or "",
                "candidates": ordered,
                "latency_ms": 0.0,
            }

        last_error = "all providers failed"
        last_category: Optional[ProviderErrorCategory] = None
        work_list = list(ordered)
        tried: set = set()
        i = 0
        while i < len(work_list):
            provider_id = work_list[i]
            i += 1
            if provider_id in tried:
                continue
            tried.add(provider_id)
            provider = self._get_or_create_provider(provider_id)
            if provider is None:
                continue
            model_name = resolved_model or provider.default_model
            kwargs = self._build_invoke_kwargs(payload)
            try:
                reservation = await quota_service.reserve(
                    provider_id, model_name,
                    messages=messages, prompt=prompt,
                    max_tokens=int(payload.get("max_tokens", 0) or 0) or None,
                )
            except Exception:
                reservation = None
            if reservation is None and quota_service.last_skip_reason:
                last_error = "quota exhausted"
                last_category = ProviderErrorCategory.RATE_LIMIT
                continue
            async def _release():
                if reservation is not None:
                    try:
                        await quota_service.release(reservation)
                    except Exception:
                        pass

            async def _commit(**kw):
                if reservation is not None:
                    try:
                        await quota_service.commit(reservation, **kw)
                    except Exception:
                        pass

            try:
                if stream:
                    injected = await self._maybe_inject_test_failure(provider_id, model_name)
                    if injected is not None:
                        await _release()
                        last_error = injected.error or last_error
                        if injected.error_category:
                            try:
                                last_category = ProviderErrorCategory(injected.error_category)
                            except ValueError:
                                last_category = ProviderErrorCategory.UNKNOWN
                        provider.record_failure(last_error, category=injected.error_category)
                        registry.record_failure(provider_id)
                        self.note_provider_result(provider_id, ok=False, error=last_error)
                        continue
                    result = await asyncio.wait_for(
                        self._stream_wrap(provider_id, provider, messages, model_name, prompt=prompt, **kwargs),
                        timeout=timeout_ms / 1000,
                    )
                    if result.ok:
                        await _commit(
                            actual_input_tokens=getattr(reservation, "estimated_input_tokens", 0),
                            actual_output_tokens=getattr(reservation, "estimated_output_tokens", 0),
                        )
                        return {"ok": True, "stream": result.raw.get("stream_gen"),
                                "provider": provider_id, "model": model_name}
                    await _release()
                    last_error = result.error or last_error
                    self.note_provider_result(provider_id, ok=False, error=last_error)
                    continue
                result = await asyncio.wait_for(
                    self._invoke_with_test_mode(
                        provider_id, provider, messages, model_name, prompt=prompt, **kwargs
                    ),
                    timeout=timeout_ms / 1000,
                )
                if result.ok:
                    usage = result.usage or {}
                    await _commit(
                        actual_input_tokens=int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
                        actual_output_tokens=int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
                    )
                    provider.record_success()
                    registry.record_success(provider_id, latency_ms=float(result.latency_ms), cost_usd=float(result.cost_usd or 0.0))
                    self.note_provider_result(provider_id, ok=True, latency_ms=float(result.latency_ms))
                    return result.to_dict()
                await _release()
                last_error = result.error or last_error
                if result.error_category:
                    normalized = str(result.error_category).replace("_", "-")
                    try:
                        last_category = ProviderErrorCategory(normalized)
                    except ValueError:
                        last_category = classify_provider_error(last_error)
                else:
                    last_category = classify_provider_error(last_error)
                provider.record_failure(last_error, category=last_category.value if last_category else None)
                registry.record_failure(provider_id)
                self.note_provider_result(provider_id, ok=False, error=last_error)
                # If this explicit provider has force_fallback, expand to auto order
                if explicit_mode and self._configs.get(provider_id, {}).get("force_fallback"):
                    for fb_pid in self._hybrid_order():
                        if fb_pid not in tried and fb_pid not in work_list[i:]:
                            work_list.append(fb_pid)
            except asyncio.TimeoutError:
                await _release()
                last_error = f"timeout after {timeout_ms}ms"
                last_category = ProviderErrorCategory.TIMEOUT
                provider.record_failure(last_error)
                registry.record_failure(provider_id)
                self.note_provider_result(provider_id, ok=False, error=last_error)
            except Exception as exc:
                await _release()
                last_error = sanitize_error_message(str(exc), known_secrets(self._configs))
                last_category = classify_provider_error(exc)
                provider.record_failure(last_error)
                registry.record_failure(provider_id)
                self.note_provider_result(provider_id, ok=False, error=last_error)
        return {
            "ok": False, "error": last_error,
            "error_category": last_category.value if last_category else None,
            "provider": "none", "latency_ms": 0.0,
        }

    async def invoke_provider(
        self, provider_id: Optional[str] = None, model: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None, timeout_ms: int = 30_000,
        stream: bool = False, pid: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self.dispatch(
            pid=pid or provider_id, model=model, payload=payload or {},
            timeout_ms=timeout_ms, stream=stream,
        )


dispatcher = ProviderDispatcher()


async def invoke_provider(
    pid: Optional[str], model: Optional[str], payload: Dict[str, Any],
    timeout_ms: int = 30_000, stream: bool = False,
) -> Dict[str, Any]:
    return await dispatcher.dispatch(pid=pid, model=model, payload=payload, timeout_ms=timeout_ms, stream=stream)


async def get_provider_health(include_hidden: bool = False) -> Dict[str, Any]:
    return await dispatcher.health_all(include_hidden=include_hidden)


def list_providers(include_hidden: bool = False) -> List[Dict[str, Any]]:
    return dispatcher.list_providers(include_hidden=include_hidden)


def get_debug_info() -> Dict[str, Any]:
    return dispatcher.debug_info()


async def select_provider(providers: list, *, preferred: Optional[str] = None) -> Any:
    if preferred is not None:
        for p in providers:
            if getattr(p, "provider_id", None) == preferred:
                return p
    for p in providers:
        try:
            health = await p.health_check()
            if health.healthy:
                return p
        except Exception:
            pass
    return providers[0] if providers else None


async def invoke_with_fallback(prompt: Any, *, providers: list) -> Any:
    last_exc: Optional[Exception] = None
    for p in providers:
        try:
            return await p.invoke(prompt)
        except Exception as exc:
            last_exc = exc
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("No providers available")
