"""
Authoritative provider dispatcher for Goblin Assistant.

Config is loaded from config/providers.toml — the SINGLE source of truth.
"""

from __future__ import annotations

import asyncio
import os
import random
from contextlib import asynccontextmanager
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
from .dispatcher_pkg.discovery import (
    build_provider_list as _build_provider_list_fn,
)
from .dispatcher_pkg.discovery import (
    get_provider as _get_provider_fn,
)
from .dispatcher_pkg.discovery import (
    get_provider_config as _get_provider_config_fn,
)
from .dispatcher_pkg.discovery import (
    is_configured as _is_configured_fn,
)
from .dispatcher_pkg.discovery import (
    list_providers as _list_providers_fn,
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
from .dispatcher_pkg.health import check_provider as _check_provider
from .dispatcher_pkg.lifecycle import (
    apply_circuit_state as _apply_circuit_state_fn,
)
from .dispatcher_pkg.lifecycle import (
    ensure_provider as _ensure_provider_fn,
)
from .dispatcher_pkg.lifecycle import (
    restore_circuit_states as _restore_circuit_states_fn,
)
from .dispatcher_pkg.lifecycle import (
    startup_preflight as _startup_preflight_fn,
)
from .dispatcher_pkg.routing import (
    _allow_self_hosted_auto_routing as _routing_allow_self_hosted,
)
from .dispatcher_pkg.routing import (
    _budget_status as _budget_status_fn,
)
from .dispatcher_pkg.routing import (
    _is_canary_attempt as _routing_is_canary_attempt,
)
from .dispatcher_pkg.routing import (
    _load_circuit_canary_percent as _load_circuit_canary_percent_fn,
)
from .dispatcher_pkg.routing import (
    _load_min_success_rate as _load_min_success_rate_fn,
)
from .dispatcher_pkg.routing import (
    _provider_costs as _routing_provider_costs,
)
from .dispatcher_pkg.routing import (
    auto_configured_candidates as _auto_configured_candidates,
)
from .dispatcher_pkg.routing import (
    candidate_order as _candidate_order_fn,
)
from .dispatcher_pkg.sanitization import (
    get_provider_logger as _get_provider_logger,
)
from .dispatcher_pkg.sanitization import (
    known_secrets as _known_secrets_from_configs,
)
from .dispatcher_pkg.sanitization import (
    sanitize_error_message as _sanitize_error_message,
)
from .dispatcher_pkg.test_mode import (
    active_test_mode_state as _active_test_mode_state,
)
from .dispatcher_pkg.test_mode import (
    apply_test_mode_delay as _apply_test_mode_delay,
)
from .dispatcher_pkg.test_mode import (
    invoke_with_test_mode as _invoke_with_test_mode,
)
from .dispatcher_pkg.test_mode import (
    maybe_inject_test_failure as _maybe_inject_test_failure,
)
from .dispatcher_pkg.warmup import (
    _load_prewarm_enabled,
    _load_prewarm_latency_threshold_ms,
)
from .dispatcher_pkg.warmup import (
    is_warmup_routing_blocked as _is_warmup_routing_blocked,
)
from .dispatcher_pkg.warmup import (
    note_provider_result as _note_warmup_result,
)
from .dispatcher_pkg.warmup import (
    start_background_tasks as _start_background_tasks,
)
from .dispatcher_pkg.warmup import (
    warmup_state_for as _warmup_state_for,
)
from .dispatcher_utils import (  # noqa: F401 — re-exported for backward compat
    CircuitBreaker,
    LoadBalancer,
    MetricsCollector,
)
from .model_registry import validate_model_alias_targets
from .provider_registry import (
    DEFAULT_PROVIDER_CLASS_MAP,
    ProviderRegistry,
    ProviderRuntimeConfig,
    build_factories_from_class_map,
)

_bootstrap_logger = structlog.get_logger(__name__)

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

_provider_toml = _load_provider_toml(logger=_bootstrap_logger)
_PROVIDER_CONFIGS: Dict[str, Dict[str, Any]] = _load_toml_providers(
    _provider_toml,
    logger=_bootstrap_logger,
)
_PROVIDER_ALIASES: Dict[str, str] = _load_aliases(_provider_toml)
_MODEL_ALIASES, _MODEL_ALIAS_PATTERNS = _load_model_aliases(_provider_toml)
_VISIBLE_PROVIDER_IDS: List[str] = _load_visible_providers(_provider_toml)
logger = _get_provider_logger(__name__, lambda: _known_secrets_from_configs(_PROVIDER_CONFIGS))
validate_model_alias_targets(
    provider_toml=_provider_toml,
    provider_configs=_PROVIDER_CONFIGS,
    logger=logger,
)


def reload_provider_catalog() -> None:
    global \
        _provider_toml, \
        _PROVIDER_CONFIGS, \
        _PROVIDER_ALIASES, \
        _MODEL_ALIASES, \
        _MODEL_ALIAS_PATTERNS, \
        _VISIBLE_PROVIDER_IDS

    _provider_toml = _load_provider_toml(logger=logger)
    _PROVIDER_CONFIGS = _load_toml_providers(_provider_toml, logger=logger)
    _PROVIDER_ALIASES = _load_aliases(_provider_toml)
    _MODEL_ALIASES, _MODEL_ALIAS_PATTERNS = _load_model_aliases(_provider_toml)
    _VISIBLE_PROVIDER_IDS = _load_visible_providers(_provider_toml)
    validate_model_alias_targets(
        provider_toml=_provider_toml,
        provider_configs=_PROVIDER_CONFIGS,
        logger=logger,
    )


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
        self._routing_min_success_rate = _load_min_success_rate_fn()
        self._circuit_canary_percent = _load_circuit_canary_percent_fn(_provider_toml)
        self._prewarm_enabled = _load_prewarm_enabled()
        self._prewarm_latency_threshold_ms = _load_prewarm_latency_threshold_ms()
        self._warmup_states: Dict[str, Dict[str, Any]] = {}
        self._warmup_task: Optional[asyncio.Task[Any]] = None
        self._pending_circuit_restores: Dict[str, Dict[str, Any]] = {}
        self._background_started = False
        self._test_mode_stack: List[Dict[str, Any]] = []
        self._random = random.Random(0)
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

    # ── Startup / Preflight ───────────────────────────────────────────────

    def _startup_preflight(self) -> None:
        _startup_preflight_fn(self, logger)

    def start_background_tasks(self) -> None:
        warmup_task_ref: List[Optional[asyncio.Task[Any]]] = [self._warmup_task]
        _start_background_tasks(
            self._warmup_states,
            self._prewarm_enabled,
            warmup_task_ref,
            [self._background_started],
            self._configs,
            self._ensure_provider,
            self.is_configured,
            self._sanitize_error,
            logger=logger,
            prewarm_latency_threshold_ms=self._prewarm_latency_threshold_ms,
        )
        self._warmup_task = warmup_task_ref[0]

    # ── Provider Lifecycle ────────────────────────────────────────────────

    def _ensure_provider(self, provider_id: str) -> Optional[ProviderAdapter]:
        return _ensure_provider_fn(self, provider_id, canonical_provider_id, logger)

    def _canonical_provider_id(self, provider_id: str) -> Optional[str]:
        return canonical_provider_id(provider_id)

    def _provider_costs(self, provider_id: str) -> tuple:
        return _routing_provider_costs(self._ensure_provider, provider_id)

    def _allow_self_hosted_auto_routing(self) -> bool:
        return _routing_allow_self_hosted()

    def _apply_circuit_state(self, provider: ProviderAdapter, state: Dict[str, Any]) -> None:
        _apply_circuit_state_fn(provider, state)

    def restore_circuit_states(self, states: Dict[str, Dict[str, Any]]) -> None:
        _restore_circuit_states_fn(self, states)

    # ── Provider Listing / Caching ────────────────────────────────────────

    def _build_provider_list(self, include_hidden: bool = False) -> List[Dict[str, Any]]:
        return _build_provider_list_fn(
            self, canonical_provider_id, _VISIBLE_PROVIDER_IDS, include_hidden=include_hidden
        )

    def list_providers(self, include_hidden: bool = False) -> List[Dict[str, Any]]:
        return _list_providers_fn(
            self, canonical_provider_id, _VISIBLE_PROVIDER_IDS, include_hidden=include_hidden
        )

    def provider_ids(self, include_hidden: bool = False) -> List[str]:
        return [item["id"] for item in self.list_providers(include_hidden=include_hidden)]

    def is_configured(self, provider_id: str) -> bool:
        return _is_configured_fn(self, canonical_provider_id, provider_id)

    def get_provider(self, provider_id: str) -> ProviderAdapter:
        return _get_provider_fn(self, canonical_provider_id, provider_id)

    def get_provider_config(self, provider_id: str) -> Dict[str, Any]:
        return _get_provider_config_fn(self, canonical_provider_id, provider_id)

    # ── Hot-Reload ────────────────────────────────────────────────────────

    def update_backend_endpoint(
        self,
        provider_id: str,
        engine: str,
        new_endpoint: str,
    ) -> None:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        if canonical_id not in self._configs:
            raise KeyError(f"Unknown provider: {provider_id!r}")

        backends = self._configs[canonical_id].get("backends", [])
        for bc in backends:
            if bc.get("engine") == engine:
                bc["endpoint"] = new_endpoint
                ep_env = str(bc.get("endpoint_env", "") or "").strip()
                if ep_env:
                    os.environ[ep_env] = new_endpoint
                break
        else:
            raise KeyError(f"No backend engine {engine!r} in {provider_id!r}")

        self._providers.pop(canonical_id, None)
        self._provider_list_cache.clear()
        self._warmup_states.pop(canonical_id, None)
        logger.info(
            "backend_endpoint_updated",
            provider=canonical_id,
            engine=engine,
            endpoint=new_endpoint,
        )

    def update_provider_endpoint(self, provider_id: str, new_endpoint: str) -> None:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        if canonical_id not in self._configs:
            raise KeyError(f"Unknown provider: {provider_id!r}")

        self._configs[canonical_id]["endpoint"] = new_endpoint

        endpoint_env = str(self._configs[canonical_id].get("endpoint_env", "") or "").strip()
        if endpoint_env:
            os.environ[endpoint_env] = new_endpoint

        self._providers.pop(canonical_id, None)
        self._provider_list_cache.clear()
        self._warmup_states.pop(canonical_id, None)

        logger.info("provider_endpoint_updated", provider=canonical_id, endpoint=new_endpoint)

    def reload_config(self) -> None:
        reload_provider_catalog()
        self._configs = _PROVIDER_CONFIGS
        self._circuit_canary_percent = _load_circuit_canary_percent_fn(_provider_toml)
        self._providers.clear()
        self._provider_list_cache.clear()
        self._warmup_states.clear()
        self._background_started = False
        logger.info("provider_catalog_reloaded")
        self.start_background_tasks()

    # ── Warmup Delegation ─────────────────────────────────────────────────

    def _warmup_state_for(self, provider_id: str) -> Dict[str, Any]:
        return _warmup_state_for(self._warmup_states, provider_id)

    def _is_warmup_routing_blocked(self, provider_id: str) -> bool:
        return _is_warmup_routing_blocked(self._warmup_states, self._configs, provider_id)

    def note_provider_result(
        self,
        provider_id: str,
        *,
        ok: bool,
        latency_ms: float = 0.0,
        error: str = "",
    ) -> None:
        config = self._configs.get(provider_id, {})
        from .dispatcher_pkg.warmup import _is_self_hosted

        if not _is_self_hosted(config):
            return
        _note_warmup_result(
            self._warmup_states,
            provider_id,
            ok=ok,
            latency_ms=latency_ms,
            error=error,
            prewarm_latency_threshold_ms=self._prewarm_latency_threshold_ms,
        )

    async def _prewarm_self_hosted_providers(self) -> None:
        from .dispatcher_pkg.warmup import _prewarm_self_hosted_providers as _run_prewarm

        await _run_prewarm(
            self._warmup_states,
            self._configs,
            self._ensure_provider,
            self.is_configured,
            self._sanitize_error,
            logger=logger,
            prewarm_latency_threshold_ms=self._prewarm_latency_threshold_ms,
        )

    # ── Routing Delegation ────────────────────────────────────────────────

    def _budget_status(self) -> Dict[str, Any]:
        from .dispatcher_pkg.routing import _load_hourly_budget_cap as _load_hourly_budget_cap_fn

        return _budget_status_fn(_load_hourly_budget_cap_fn, _provider_toml)

    def _priority_order(self) -> List[str]:
        from .dispatcher_pkg.routing import priority_order

        return priority_order(self.list_providers)

    def _cheapest_order(self) -> List[str]:
        from .dispatcher_pkg.routing import cheapest_order

        return cheapest_order(
            self._ensure_provider,
            self._configs,
            self.list_providers,
            provider_toml=_provider_toml,
            logger=logger,
        )

    def _hybrid_order(self) -> List[str]:
        from .dispatcher_pkg.routing import hybrid_order

        return hybrid_order(
            self._ensure_provider,
            self._configs,
            self.list_providers,
            provider_toml=_provider_toml,
            logger=logger,
        )

    def _local_order(self) -> List[str]:
        from .dispatcher_pkg.routing import local_order

        return local_order(
            self._ensure_provider,
            self._configs,
            self.list_providers,
            provider_toml=_provider_toml,
            logger=logger,
        )

    def _is_auto_routing_candidate(self, provider_id: str) -> bool:
        from .dispatcher_pkg.routing import is_auto_routing_candidate

        return is_auto_routing_candidate(self._configs, provider_id)

    def _auto_configured_candidates(self, candidates: List[str]) -> List[str]:
        return _auto_configured_candidates(
            self._configs,
            candidates,
            self.is_configured,
            self._is_warmup_routing_blocked,
        )

    def _apply_budget_rerank(self, candidates: List[str], *, routing_mode: str) -> List[str]:
        budget_status = self._budget_status()
        if not budget_status["over_budget"]:
            return candidates

        def _sort_key(pid: str) -> tuple:
            input_cost, output_cost = self._provider_costs(pid)
            total_cost = input_cost + output_cost
            config = self._configs.get(pid, {})
            return (
                0.0 if total_cost <= 0 else 1.0,
                total_cost,
                int(config.get("priority_tier", 999)),
            )

        re_ranked = sorted(candidates, key=_sort_key)
        logger.warning(
            "routing_budget_soft_rerank",
            routing_mode=routing_mode,
            current_hour_spend_usd=budget_status["current_hour_spend_usd"],
            cap_usd=budget_status["cap_usd"],
            original_candidates=candidates,
            rank_order=re_ranked,
        )
        return re_ranked

    def _candidate_order(self, provider_id: Optional[str]) -> List[str]:
        def _priority_list_fn(include_hidden: bool = False) -> List[Dict[str, Any]]:
            _ = include_hidden
            return [{"id": pid} for pid in self._priority_order()]

        return _candidate_order_fn(
            provider_id,
            canonical_provider_id,
            self._configs,
            self._ensure_provider,
            _priority_list_fn,
            provider_toml=_provider_toml,
            logger=logger,
        )

    def _is_canary_attempt(
        self,
        provider_id: str,
        model: Optional[str],
    ) -> bool:
        return _routing_is_canary_attempt(self._ensure_provider, provider_id, model)

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

    # ── Model Alias Resolution ────────────────────────────────────────────

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

    # ── Test Mode Delegation ──────────────────────────────────────────────

    def _active_test_mode_state(self, provider_id: str) -> Optional[Dict[str, Any]]:
        return _active_test_mode_state(self._test_mode_stack, provider_id)

    async def _apply_test_mode_delay(self, provider_id: str) -> None:
        await _apply_test_mode_delay(self._test_mode_stack, provider_id)

    async def _maybe_inject_test_failure(
        self,
        provider_id: str,
        model: str,
    ) -> Optional[ProviderResult]:
        return await _maybe_inject_test_failure(
            self._test_mode_stack,
            provider_id,
            model,
            provider_error_category_fn=self._provider_error_category,
        )

    async def _invoke_with_test_mode(
        self,
        provider_id: str,
        provider: ProviderAdapter,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> ProviderResult:
        return await _invoke_with_test_mode(
            self._test_mode_stack,
            provider_id,
            provider,
            messages,
            model,
            sanitize_error_fn=self._sanitize_error,
            provider_error_category_fn=self._provider_error_category,
            **kwargs,
        )

    @asynccontextmanager
    async def test_mode(self, profiles: Dict[str, Dict[str, Any]]):
        """Inject deterministic failure profiles for routing tests.

        Supported profile keys:
        - ``fail_after_calls``: fail on the N+1 call and later.
        - ``fail_probability``: randomly fail each call with this probability.
        - ``latency_ms``: add artificial latency before invoke/stream calls.
        - ``error_category``: explicit ProviderErrorCategory for injected failures.
        - ``error``: custom failure message.
        - ``health_check``: synthetic health result with ``healthy``,
          ``billing_issue``, ``latency_ms``, and ``error`` fields.
        """
        state = {
            "profiles": {
                canonical_provider_id(pid) or pid: dict(profile)
                for pid, profile in profiles.items()
            },
            "calls": {},
        }
        self._test_mode_stack.append(state)
        try:
            yield self
        finally:
            with_state = [item for item in self._test_mode_stack if item is not state]
            self._test_mode_stack = with_state

    # ── Health Checks ────────────────────────────────────────────────────

    async def check_provider(self, provider_id: str) -> Dict[str, Any]:
        return await _check_provider(self, provider_id, logger=logger)

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
                "circuit_breaker": item.get("circuit_breaker", {}),
            }
            for item in inventory
        }

    # ── Stream Wrap / Dispatch ────────────────────────────────────────────

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
                "circuit_breaker": (
                    self._providers[item["id"]].circuit_status()
                    if item["id"] in self._providers
                    else {}
                ),
                "hidden": item["hidden"],
                "capabilities": item["capabilities"],
                "default_model": item["default_model"],
                "warmup": self._warmup_state_for(item["id"]),
            }
            for item in self.list_providers(include_hidden=True)
        ]

        return {
            "routing_table": routing_table,
            "registry_stats": registry.snapshot(),
            "registry_metrics": registry.metrics_snapshot(),
            "registry_persisted_snapshot": registry.persisted_snapshot(),
            "registry_persistence": registry.persistence_status(),
            "budget_status": self._budget_status(),
            "warmup_states": dict(self._warmup_states),
            "routing_min_success_rate": self._routing_min_success_rate,
            "circuit_canary_percent": self._circuit_canary_percent,
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


# ---------------------------------------------------------------------------
# Standalone helpers expected by tests
# ---------------------------------------------------------------------------


async def select_provider(providers: list, *, preferred: Optional[str] = None) -> Any:
    """Select the best provider from a list based on health and latency."""
    if preferred:
        for p in providers:
            health = await p.health_check()
            if p.provider_id == preferred and health.healthy:
                return p

    healthy = []
    for p in providers:
        health = await p.health_check()
        if health.healthy:
            healthy.append((health.latency_ms, p))

    if healthy:
        healthy.sort(key=lambda x: x[0])
        return healthy[0][1]

    # All unhealthy — pick lowest latency anyway
    all_checked = []
    for p in providers:
        health = await p.health_check()
        all_checked.append((health.latency_ms, p))
    all_checked.sort(key=lambda x: x[0])
    return all_checked[0][1] if all_checked else providers[0]


async def invoke_with_fallback(prompt: str, *, providers: list) -> Any:
    """Try each provider in order; raise if all fail."""
    last_exc: Optional[Exception] = None
    for p in providers:
        try:
            return await p.invoke(prompt)
        except Exception as exc:
            last_exc = exc
    raise last_exc or RuntimeError("No providers available")
