"""Shared provider pricing and quota configuration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .provider_config_runtime import load_provider_config


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


def _normalize_provider_config(provider_id: str, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if config and any(
        key in config
        for key in (
            "costs",
            "cost_input_per1k",
            "cost_output_per1k",
            "rate_limits",
            "rate_limit_per_min",
        )
        ):
        return dict(config)
    loaded = load_provider_config(use_cache=False).get_provider(provider_id)
    if loaded is not None:
        return loaded.model_dump()
    return dict(config or {})


def resolve_model_pricing(
    provider_id: str,
    model: Optional[str] = None,
    *,
    config: Optional[Dict[str, Any]] = None,
    default_input_per1k: float = 0.0,
    default_output_per1k: float = 0.0,
) -> ModelPricing:
    provider_cfg = _normalize_provider_config(provider_id, config)
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
                input_per1k=float(
                    cost_dict.get("input_per1k", cost_dict.get("input", default_input_per1k))
                ),
                output_per1k=float(
                    cost_dict.get("output_per1k", cost_dict.get("output", default_output_per1k))
                ),
            )

    legacy_input = provider_cfg.get("cost_input_per1k", default_input_per1k)
    legacy_output = provider_cfg.get("cost_output_per1k", default_output_per1k)
    return ModelPricing(
        input_per1k=float(legacy_input or default_input_per1k),
        output_per1k=float(legacy_output or default_output_per1k),
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
        input_tokens * pricing.input_per1k / 1000.0
        + output_tokens * pricing.output_per1k / 1000.0
    )
