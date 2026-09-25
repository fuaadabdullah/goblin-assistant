"""Shared provider pricing and quota configuration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Optional

import structlog

from .provider_config_runtime import load_provider_config

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ModelPricing:
    input_per1k: float = 0.0
    output_per1k: float = 0.0


@dataclass(frozen=True)
class RateLimitConfig:
    requests_per_minute: int = 0
    tokens_per_minute: int = 0
    concurrency: int = 0


def _as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
        if isinstance(dumped, dict):
            return dumped
    return {}


def _normalize_provider_config(
    provider_id: str, config: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    if config and any(
        key in config
        for key in (
            "costs",
            "cost_input_per1k",
            "cost_output_per1k",
            "cost_input_per_1k",
            "cost_output_per_1k",
            "rate_limits",
            "rate_limit_per_min",
        )
    ):
        return dict(config)
    loaded = load_provider_config(use_cache=False).get_provider(provider_id)
    if loaded is not None:
        return loaded.model_dump()
    return dict(config or {})


@lru_cache(maxsize=256)
def _litellm_cost_lookup(model: str) -> Optional[ModelPricing]:
    """Look up per-1k pricing from LiteLLM's upstream-maintained model cost map
    (https://github.com/BerriAI/litellm). Returns ``None`` if LiteLLM isn't
    importable or doesn't recognize *model*, so callers fall back to the local
    ``providers.toml`` table — which stays authoritative for self-hosted/custom
    backends LiteLLM has no pricing for.
    """
    try:
        import litellm

        prompt_cost, completion_cost = litellm.cost_per_token(
            model=model, prompt_tokens=1000, completion_tokens=1000
        )
    except Exception as exc:
        logger.debug("litellm_pricing_lookup_failed", model=model, error=str(exc))
        return None
    if not prompt_cost and not completion_cost:
        return None
    return ModelPricing(input_per1k=float(prompt_cost), output_per1k=float(completion_cost))


def _resolve_litellm_pricing(provider_id: str, model: Optional[str]) -> Optional[ModelPricing]:
    if not model:
        return None
    pricing = _litellm_cost_lookup(model)
    if pricing is not None:
        return pricing
    # Some providers need an explicit "<provider>/<model>" hint for LiteLLM to
    # disambiguate — mirrors the litellm_provider/model pairing router_service.py
    # already builds for the LiteLLM Router's own model list.
    return _litellm_cost_lookup(f"{provider_id}/{model}")


def resolve_model_pricing(
    provider_id: str,
    model: Optional[str] = None,
    *,
    config: Optional[Dict[str, Any]] = None,
) -> ModelPricing:
    """
    Resolve per-model pricing, preferring LiteLLM's upstream-maintained model
    cost map so pricing can't quietly go stale. Falls back to the local
    ``providers.toml`` table when LiteLLM doesn't recognize the model — this is
    what keeps self-hosted/custom backends (e.g. Ollama, a private llama.cpp
    node) working, since LiteLLM has no pricing data for those.

    The ``providers.toml`` fallback looks up costs in the
    ``[providers.<id>.costs]`` section keyed by:
      1. the exact *model* name,
      2. the provider's *default_model*,
      3. ``"default"``,
      4. ``"*"`` (wildcard fallback).

    If nothing is found anywhere, returns ``ModelPricing(0.0, 0.0)``.
    """
    provider_cfg = _normalize_provider_config(provider_id, config)

    litellm_pricing = _resolve_litellm_pricing(
        provider_id, model or provider_cfg.get("default_model")
    )
    if litellm_pricing is not None:
        return litellm_pricing

    costs = _as_dict(provider_cfg.get("costs"))
    candidate_keys = [
        key
        for key in (
            model,
            provider_cfg.get("default_model"),
            "default",
            "*",
        )
        if isinstance(key, str) and key
    ]
    for key in candidate_keys:
        raw_cost = costs.get(key)
        if not raw_cost:
            continue
        cost_dict = _as_dict(raw_cost)
        if cost_dict:
            return ModelPricing(
                input_per1k=float(cost_dict.get("input_per1k", cost_dict.get("input", 0.0))),
                output_per1k=float(cost_dict.get("output_per1k", cost_dict.get("output", 0.0))),
            )

    # Legacy top-level fields — accept both spellings (TOML uses per1k, config dicts use per_1k)
    legacy_input = provider_cfg.get("cost_input_per1k") or provider_cfg.get(
        "cost_input_per_1k", 0.0
    )
    legacy_output = provider_cfg.get("cost_output_per1k") or provider_cfg.get(
        "cost_output_per_1k", 0.0
    )
    return ModelPricing(
        input_per1k=float(legacy_input or 0.0),
        output_per1k=float(legacy_output or 0.0),
    )


def resolve_rate_limit(
    provider_id: str,
    model: Optional[str] = None,
    *,
    config: Optional[Dict[str, Any]] = None,
) -> RateLimitConfig:
    provider_cfg = _normalize_provider_config(provider_id, config)
    rate_limits = _as_dict(provider_cfg.get("rate_limits"))
    candidate_keys = [
        key
        for key in (
            model,
            provider_cfg.get("default_model"),
            "default",
            "*",
        )
        if isinstance(key, str) and key
    ]
    for key in candidate_keys:
        raw_limit = rate_limits.get(key)
        if not raw_limit:
            continue
        limit_dict = _as_dict(raw_limit)
        if limit_dict:
            return RateLimitConfig(
                requests_per_minute=int(
                    limit_dict.get("requests_per_minute", limit_dict.get("requests", 0)) or 0
                ),
                tokens_per_minute=int(
                    limit_dict.get("tokens_per_minute", limit_dict.get("tokens", 0)) or 0
                ),
                concurrency=int(limit_dict.get("concurrency", 0) or 0),
            )

    legacy_requests = int(provider_cfg.get("rate_limit_per_min", 0) or 0)
    return RateLimitConfig(requests_per_minute=legacy_requests)


@dataclass(frozen=True)
class CircuitBreakerThresholds:
    soft_threshold: int = 2
    failure_threshold: int = 3
    recovery_timeout_seconds: float = 30.0


def resolve_circuit_breaker_thresholds() -> CircuitBreakerThresholds:
    """Resolve provider circuit-breaker thresholds from the single source of
    truth (providers.toml [load_balancing]) instead of hardcoding them at
    each call site. Respects config reload the same way resolve_model_pricing
    does, so dispatcher.reload_config() picks up threshold changes too."""
    load_balancing = load_provider_config(use_cache=True).load_balancing
    return CircuitBreakerThresholds(
        soft_threshold=load_balancing.circuit_breaker_soft_threshold,
        failure_threshold=load_balancing.circuit_breaker_failure_threshold,
        recovery_timeout_seconds=float(load_balancing.circuit_breaker_recovery_timeout),
    )


def resolve_canonical_model(model: Optional[str]) -> Optional[str]:
    if not model:
        return None

    provider_toml = load_provider_config(use_cache=True)
    provider_id, canonical_model = provider_toml.resolve_model_alias(model)
    if canonical_model:
        return canonical_model
    return model


def resolve_model_budget(model: Optional[str]) -> RateLimitConfig:
    canonical_model = resolve_canonical_model(model)
    if not canonical_model:
        return RateLimitConfig()

    provider_toml = load_provider_config(use_cache=True)
    raw_budget = provider_toml.get_model_budget(canonical_model)
    return RateLimitConfig(
        requests_per_minute=int(raw_budget.requests_per_minute or 0),
        tokens_per_minute=int(raw_budget.tokens_per_minute or 0),
        concurrency=int(raw_budget.concurrency or 0),
    )


def estimate_cost(
    provider_id: str,
    input_tokens: int,
    output_tokens: int,
    *,
    model: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> float:
    pricing = resolve_model_pricing(
        provider_id,
        model,
        config=config,
    )
    return (
        input_tokens * pricing.input_per1k / 1000.0 + output_tokens * pricing.output_per1k / 1000.0
    )
