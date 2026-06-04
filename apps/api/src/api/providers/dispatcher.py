"""
Authoritative provider dispatcher for Goblin Assistant.

Config is loaded from config/providers.toml — the SINGLE source of truth.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional

import structlog

from .base import (
    BaseProvider,
    ProviderErrorCategory,
    ProviderResult,
    classify_provider_error,
)
from .contracts import ProviderAdapter
from .dispatcher_pkg.config import (
    expand_alias_template as _expand_alias_template,
)
from .dispatcher_pkg.config import (
    load_aliases as _load_aliases,
)
from .dispatcher_pkg.config import (
    load_model_aliases as _load_model_aliases,
)
from .dispatcher_pkg.config import (
    load_provider_toml as _load_provider_toml,
)
from .dispatcher_pkg.config import (
    load_toml_providers as _load_toml_providers,
)
from .dispatcher_pkg.config import (
    load_visible_providers as _load_visible_providers,
)
from .dispatcher_pkg.config import (
    normalize_token as _normalize_token,
)
from .dispatcher_pkg.execution import (
    build_invoke_kwargs as _build_invoke_kwargs,
)
from .dispatcher_pkg.execution import (
    dispatch_request as _dispatch_request,
)
from .dispatcher_pkg.execution import (
    provider_error_category as _provider_error_category,
)
from .dispatcher_pkg.execution import (
    stream_wrap as _stream_wrap,
)
from .dispatcher_pkg.sanitization import (
    known_secrets as _known_secrets_from_configs,
)
from .dispatcher_pkg.sanitization import (
    sanitize_error_message as _sanitize_error_message,
)
from .provider_registry import (
    DEFAULT_PROVIDER_CLASS_MAP,
    ProviderRegistry,
    ProviderRuntimeConfig,
    build_factories_from_class_map,
)
from .routing_strategies import rank_cheapest, rank_hybrid, rank_local

logger = structlog.get_logger(__name__)

# Preserve historical module attribute for monkeypatch-based tests/importers.
_CLASSIFY_PROVIDER_ERROR = classify_provider_error

try:
    from dotenv import load_dotenv

    load_dotenv()
    load_dotenv(".env.local")
except ImportError:
    pass

# Compatibility seam for tests that monkeypatch the dispatcher class map.
_PROVIDER_CLASS_MAP: Dict[str, type[BaseProvider]] = dict(DEFAULT_PROVIDER_CLASS_MAP)

# ── Load once ─────────────────────────────────────────────────────────────

_provider_toml = _load_provider_toml(logger=logger)
_PROVIDER_CONFIGS: Dict[str, Dict[str, Any]] = _load_toml_providers(
    _provider_toml,
    logger=logger,
)
_PROVIDER_ALIASES: Dict[str, str] = _load_aliases(_provider_toml)
_MODEL_ALIASES, _MODEL_ALIAS_PATTERNS = _load_model_aliases(_provider_toml)
_VISIBLE_PROVIDER_IDS: List[str] = _load_visible_providers(_provider_toml)


def canonical_provider_id(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = _normalize_token(value)
    if not normalized:
        return None
    return _PROVIDER_ALIASES.get(normalized, normalized)


class ProviderDispatcher:
    DEFAULT_HEALTH_CHECK_TIMEOUT_MS = 5_000

    def __init__(
        self,
        *,
        configs: Optional[Dict[str, Dict[str, Any]]] = None,
        class_map: Optional[Dict[str, type[BaseProvider]]] = None,
    ) -> None:
        self._using_custom_configs = configs is not None
        self._configs: Dict[str, Dict[str, Any]] = (
            configs if configs is not None else _PROVIDER_CONFIGS
        )
        self._class_map: Dict[str, type[BaseProvider]] = (
            class_map if class_map is not None else _PROVIDER_CLASS_MAP
        )
        self._registry = ProviderRegistry(
            factories=build_factories_from_class_map(self._class_map),
        )
        self._providers: Dict[str, ProviderAdapter] = {}
        self._provider_list_cache: Dict[bool, List[Dict[str, Any]]] = {}
        self._routing_min_success_rate = self._load_min_success_rate()
        self._startup_preflight()

    def _known_secrets(self) -> List[str]:
        return _known_secrets_from_configs(self._configs)

    def _sanitize_error(self, value: Any) -> str:
        return _sanitize_error_message(str(value), self._known_secrets())

    def _runtime_config(self, provider_id: str) -> Optional[ProviderRuntimeConfig]:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        raw_config = self._configs.get(canonical_id, {})
        if not isinstance(raw_config, dict):
            return None
        try:
            return self._registry.runtime_config(canonical_id, raw_config)
        except (TypeError, ValueError) as exc:
            logger.warning(
                "provider_runtime_config_invalid",
                provider=canonical_id,
                error=str(exc),
            )
            return None

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

    def _ensure_provider(self, provider_id: str) -> Optional[ProviderAdapter]:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        provider = self._providers.get(canonical_id)
        if provider is not None:
            return provider

        if canonical_id not in self._class_map:
            logger.warning("no_class_for_provider", provider=canonical_id)
            return None

        source_config = dict(self._configs.get(canonical_id, {}))
        try:
            provider = self._registry.create_from_source(canonical_id, source_config)
        except Exception as exc:
            logger.warning(
                "provider_init_failed",
                provider=canonical_id,
                error=self._sanitize_error(exc),
            )
            return None
        self._providers[canonical_id] = provider
        return provider

    def _build_registry(self) -> None:
        for provider_id in self._configs:
            self._ensure_provider(provider_id)

    def _build_provider_list(
        self,
        include_hidden: bool = False,
    ) -> List[Dict[str, Any]]:
        providers: List[Dict[str, Any]] = []
        if include_hidden or self._using_custom_configs or not _VISIBLE_PROVIDER_IDS:
            provider_ids = list(self._configs.keys())
        else:
            provider_ids = []
            seen: set[str] = set()
            for entry in _VISIBLE_PROVIDER_IDS:
                canonical_id = canonical_provider_id(entry) or entry
                if canonical_id not in self._configs or canonical_id in seen:
                    continue
                seen.add(canonical_id)
                provider_ids.append(canonical_id)

        for provider_id in provider_ids:
            runtime_cfg = self._runtime_config(provider_id)
            config = (
                runtime_cfg.to_provider_dict()
                if runtime_cfg is not None
                else dict(self._configs.get(provider_id, {}))
            )
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
        return providers

    def list_providers(
        self,
        include_hidden: bool = False,
    ) -> List[Dict[str, Any]]:
        cached = self._provider_list_cache.get(include_hidden)
        if cached is not None:
            return [dict(item) for item in cached]

        providers = self._build_provider_list(include_hidden=include_hidden)
        if include_hidden or self._using_custom_configs or not _VISIBLE_PROVIDER_IDS:
            providers.sort(
                key=lambda item: (
                    int(item.get("priority_tier", 999)),
                    str(item.get("id", "")),
                )
            )
        self._provider_list_cache[include_hidden] = [dict(item) for item in providers]
        return [dict(item) for item in providers]

    def provider_ids(
        self,
        include_hidden: bool = False,
    ) -> List[str]:
        return [item["id"] for item in self.list_providers(include_hidden=include_hidden)]

    def _is_self_hosted(self, config: Dict[str, Any]) -> bool:
        return str(config.get("tier", "")) == "self_hosted"

    def is_configured(self, provider_id: str) -> bool:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        runtime_cfg = self._runtime_config(canonical_id)
        return runtime_cfg.is_configured() if runtime_cfg is not None else False

    def get_provider(self, provider_id: str) -> ProviderAdapter:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        provider = self._ensure_provider(canonical_id)
        if provider is None:
            raise KeyError(f"Unknown provider: {provider_id}")
        return provider

    def get_provider_config(self, provider_id: str) -> Dict[str, Any]:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        return dict(self._configs.get(canonical_id, {}))

    def update_provider_endpoint(self, provider_id: str, new_endpoint: str) -> None:
        """Hot-reload a provider's endpoint URL in-memory without restart."""
        canonical_id = canonical_provider_id(provider_id) or provider_id
        if canonical_id not in self._configs:
            raise KeyError(f"Unknown provider: {provider_id!r}")

        self._configs[canonical_id]["endpoint"] = new_endpoint

        endpoint_env = str(self._configs[canonical_id].get("endpoint_env", "") or "").strip()
        if endpoint_env:
            os.environ[endpoint_env] = new_endpoint

        self._providers.pop(canonical_id, None)
        self._provider_list_cache.clear()

        logger.info("provider_endpoint_updated", provider=canonical_id, endpoint=new_endpoint)

    def _provider_costs(self, provider_id: str) -> tuple[float, float]:
        provider = self._ensure_provider(provider_id)
        if provider is None:
            return (float("inf"), float("inf"))
        return (provider.COST_INPUT_PER_1K, provider.COST_OUTPUT_PER_1K)

    def _priority_order(self) -> List[str]:
        return [item["id"] for item in self.list_providers(include_hidden=False)]

    def _cheapest_order(self) -> List[str]:
        candidates = self._priority_order()
        provider_costs = {p: self._provider_costs(p) for p in candidates}
        return rank_cheapest(candidates, provider_costs)

    def _hybrid_order(self) -> List[str]:
        candidates = self._priority_order()
        provider_costs = {p: self._provider_costs(p) for p in candidates}
        return rank_hybrid(candidates, provider_costs)

    def _local_order(self) -> List[str]:
        providers = self.list_providers(include_hidden=False)
        local_candidates = [
            item["id"]
            for item in providers
            if item["local_routing"] or item["tier"] == "self_hosted"
        ]
        return rank_local(local_candidates)

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

    def _resolve_pattern_model_alias(self, model: str) -> Optional[tuple[str, str]]:
        for compiled_pattern, provider_template, model_template in _MODEL_ALIAS_PATTERNS:
            match = compiled_pattern.fullmatch(model)
            if match is None:
                continue
            captures = tuple(match.groups())
            provider = _expand_alias_template(provider_template, captures).strip()
            resolved_model = _expand_alias_template(model_template, captures).strip()
            if provider and resolved_model:
                return provider, resolved_model
        return None

    def _resolve_model_alias(
        self,
        provider_id: Optional[str],
        model: Optional[str],
    ) -> tuple[Optional[str], Optional[str]]:
        if model is None:
            return provider_id, model

        alias = _MODEL_ALIASES.get(model)
        if alias is None:
            alias = self._resolve_pattern_model_alias(model)
        if alias is None:
            return provider_id, model

        alias_provider, alias_model = alias
        alias_provider = canonical_provider_id(alias_provider) or alias_provider
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
        if canonical_id and canonical_id in self._configs:
            return [canonical_id]
        return []

    async def check_provider(self, provider_id: str) -> Dict[str, Any]:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        config = self._configs.get(canonical_id, {})
        provider = self._ensure_provider(canonical_id)
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

        timeout_ms = int(
            config.get("health_check_timeout_ms", self.DEFAULT_HEALTH_CHECK_TIMEOUT_MS),
        )
        try:
            health = await asyncio.wait_for(
                provider.health_check(),
                timeout=max(1, timeout_ms) / 1000,
            )
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
                "health_reason": self._sanitize_error(getattr(health, "error", "") or ""),
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
                "health_reason": f"timed out after {timeout_ms}ms",
                "billing_issue": False,
                "is_selectable": False,
                "latency_ms": float(timeout_ms),
            }
        except Exception as exc:
            return {
                "id": canonical_id,
                "configured": True,
                "healthy": False,
                "health": "unhealthy",
                "health_reason": self._sanitize_error(exc),
                "billing_issue": False,
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
        for meta, health in zip(providers, checks):
            if isinstance(health, Exception):
                health = {
                    "configured": False,
                    "healthy": False,
                    "health": "unknown",
                    "health_reason": self._sanitize_error(health),
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
        return await _stream_wrap(
            self,
            provider_id,
            provider,
            messages,
            model,
            logger=logger,
            **kwargs,
        )

    @staticmethod
    def _provider_error_category(
        value: Any,
        fallback_error: str,
    ) -> Optional[ProviderErrorCategory]:
        return _provider_error_category(value, fallback_error)

    @staticmethod
    def _build_invoke_kwargs(payload: Dict[str, Any]) -> Dict[str, Any]:
        return _build_invoke_kwargs(payload)

    async def dispatch(
        self,
        pid: Optional[str],
        model: Optional[str],
        payload: Dict[str, Any],
        *,
        timeout_ms: int = 30_000,
        stream: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        return await _dispatch_request(
            self,
            pid=pid,
            model=model,
            payload=payload,
            timeout_ms=timeout_ms,
            stream=stream,
            dry_run=dry_run,
            logger=logger,
        )

    def debug_info(self) -> Dict[str, Any]:
        """Return internal dispatcher state for debugging and support."""
        from ..routing.router import registry

        routing_table = [
            {
                "provider_id": item["id"],
                "name": item["name"],
                "priority_tier": item["priority_tier"],
                "tier": item["tier"],
                "local_routing": item["local_routing"],
                "configured": self.is_configured(item["id"]),
                "instantiated": item["id"] in self._providers,
                "hidden": item["hidden"],
                "capabilities": item["capabilities"],
                "default_model": item["default_model"],
            }
            for item in self.list_providers(include_hidden=True)
        ]

        return {
            "routing_table": routing_table,
            "registry_stats": registry.snapshot(),
            "routing_min_success_rate": self._routing_min_success_rate,
            "model_aliases": {k: list(v) for k, v in _MODEL_ALIASES.items()},
            "model_alias_patterns": [pattern.pattern for pattern, _, _ in _MODEL_ALIAS_PATTERNS],
            "provider_aliases": dict(_PROVIDER_ALIASES),
            "visible_provider_order": list(_VISIBLE_PROVIDER_IDS),
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


def get_debug_info() -> Dict[str, Any]:
    return dispatcher.debug_info()
