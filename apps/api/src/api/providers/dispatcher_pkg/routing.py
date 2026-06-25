"""Provider ordering, budget reranking, and capability queries."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from ..pricing import resolve_model_pricing
from ..routing_strategies import rank_cheapest, rank_hybrid, rank_local


def _load_hourly_budget_cap(provider_toml: Any) -> float:
    raw_value = os.getenv("ROUTING_MAX_BUDGET_PER_HOUR", "").strip()
    if not raw_value:
        raw_value = str(
            getattr(
                getattr(getattr(provider_toml, "default", object()), "cost_optimization", object()),
                "max_budget_per_hour",
                0.0,
            )
        )
    try:
        return max(0.0, float(raw_value))
    except (TypeError, ValueError):
        return 0.0


def _load_min_success_rate() -> float:
    raw_value = os.getenv("ROUTING_MIN_SUCCESS_RATE", "0.3").strip()
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return 0.3
    return max(0.0, min(1.0, value))


def _load_circuit_canary_percent(provider_toml: Any) -> float:
    raw_value = os.getenv("PROVIDER_CIRCUIT_CANARY_PERCENT", "").strip()
    if not raw_value:
        raw_value = str(
            getattr(
                getattr(provider_toml, "load_balancing", object()),
                "circuit_breaker_canary_percent",
                0.1,
            )
        )
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return 0.1
    if value > 1:
        value /= 100
    return max(0.0, min(1.0, value))


def _allow_self_hosted_auto_routing() -> bool:
    return os.getenv("ENABLE_SELF_HOSTED_AUTO_ROUTING", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _provider_costs(
    ensure_provider_fn,
    provider_id: str,
) -> tuple[float, float]:
    provider = ensure_provider_fn(provider_id)
    if provider is None:
        return (float("inf"), float("inf"))
    pricing = resolve_model_pricing(
        provider.provider_id,
        provider.default_model or None,
        config=provider.config,
    )
    return (pricing.input_per1k, pricing.output_per1k)


def _budget_sort_key(
    ensure_provider_fn,
    provider_id: str,
    configs: Dict[str, Dict[str, Any]],
) -> tuple[float, float, int]:
    input_cost, output_cost = _provider_costs(ensure_provider_fn, provider_id)
    total_cost = input_cost + output_cost
    config = configs.get(provider_id, {})
    return (
        0.0 if total_cost <= 0 else 1.0,
        total_cost,
        int(config.get("priority_tier", 999)),
    )


def _budget_status(
    load_hourly_budget_cap_fn,
    provider_toml: Any,
) -> Dict[str, Any]:
    cap = load_hourly_budget_cap_fn(provider_toml)

    # Deferred import to avoid circular dependency at module level
    from ...routing.router import registry

    spend_by_provider = registry.current_hour_spend()
    total_spend = round(sum(spend_by_provider.values()), 6)
    return {
        "cap_usd": round(cap, 6),
        "current_hour_spend_usd": total_spend,
        "current_hour_spend_by_provider": {
            provider_id: round(spend, 6) for provider_id, spend in spend_by_provider.items()
        },
        "over_budget": bool(cap > 0 and total_spend >= cap),
    }


def _apply_budget_rerank(
    ensure_provider_fn,
    configs: Dict[str, Dict[str, Any]],
    candidates: List[str],
    *,
    routing_mode: str,
    provider_toml: Any,
    logger: Any,
) -> List[str]:
    budget_status = _budget_status(
        _load_hourly_budget_cap,
        provider_toml,
    )
    if not budget_status["over_budget"]:
        return candidates
    re_ranked = sorted(
        candidates,
        key=lambda pid: _budget_sort_key(ensure_provider_fn, pid, configs),
    )
    logger.warning(
        "routing_budget_soft_rerank",
        routing_mode=routing_mode,
        current_hour_spend_usd=budget_status["current_hour_spend_usd"],
        cap_usd=budget_status["cap_usd"],
        original_candidates=candidates,
        rank_order=re_ranked,
    )
    return re_ranked


def priority_order(
    list_providers_fn,
) -> List[str]:
    return [item["id"] for item in list_providers_fn(include_hidden=False)]


def cheapest_order(
    ensure_provider_fn,
    configs: Dict[str, Dict[str, Any]],
    list_providers_fn,
    *,
    provider_toml: Any,
    logger: Any,
) -> List[str]:
    candidates = priority_order(list_providers_fn)
    provider_costs = {p: _provider_costs(ensure_provider_fn, p) for p in candidates}
    return _apply_budget_rerank(
        ensure_provider_fn,
        configs,
        rank_cheapest(candidates, provider_costs),
        routing_mode="cheapest",
        provider_toml=provider_toml,
        logger=logger,
    )


def hybrid_order(
    ensure_provider_fn,
    configs: Dict[str, Dict[str, Any]],
    list_providers_fn,
    *,
    provider_toml: Any,
    logger: Any,
) -> List[str]:
    candidates = priority_order(list_providers_fn)
    provider_costs = {p: _provider_costs(ensure_provider_fn, p) for p in candidates}
    return _apply_budget_rerank(
        ensure_provider_fn,
        configs,
        rank_hybrid(candidates, provider_costs),
        routing_mode="auto",
        provider_toml=provider_toml,
        logger=logger,
    )


def local_order(
    ensure_provider_fn,
    configs: Dict[str, Dict[str, Any]],
    list_providers_fn,
    *,
    provider_toml: Any,
    logger: Any,
) -> List[str]:
    providers = list_providers_fn(include_hidden=False)
    local_candidates = [
        item["id"]
        for item in providers
        if bool(item.get("local_routing", False)) or item.get("tier") == "self_hosted"
    ]
    return _apply_budget_rerank(
        ensure_provider_fn,
        configs,
        rank_local(local_candidates),
        routing_mode="local",
        provider_toml=provider_toml,
        logger=logger,
    )


def is_auto_routing_candidate(configs: Dict[str, Dict[str, Any]], provider_id: str) -> bool:
    config = configs.get(provider_id, {})
    if not config:
        return False
    if config.get("local_routing") or str(config.get("tier", "")) == "self_hosted":
        return _allow_self_hosted_auto_routing()
    return True


def auto_configured_candidates(
    configs: Dict[str, Dict[str, Any]],
    candidates: List[str],
    is_configured_fn,
    is_warmup_routing_blocked_fn,
) -> List[str]:
    configured = [p for p in candidates if is_configured_fn(p)]
    filtered = [p for p in configured if is_auto_routing_candidate(configs, p)]
    if filtered:
        configured = filtered
    configured = [p for p in configured if not is_warmup_routing_blocked_fn(p)]
    try:
        from ..services.provider_health import health_monitor

        healthy = [p for p in configured if health_monitor.is_available(p)]
        if healthy:
            return healthy
    except Exception:
        pass
    return configured


def candidate_order(
    provider_id: Optional[str],
    canonical_provider_id_fn,
    configs: Dict[str, Dict[str, Any]],
    ensure_provider_fn,
    list_providers_fn,
    *,
    provider_toml: Any,
    logger: Any,
) -> List[str]:
    if provider_id in (None, "auto"):
        return hybrid_order(
            ensure_provider_fn,
            configs,
            list_providers_fn,
            provider_toml=provider_toml,
            logger=logger,
        )
    if provider_id == "cheapest":
        return cheapest_order(
            ensure_provider_fn,
            configs,
            list_providers_fn,
            provider_toml=provider_toml,
            logger=logger,
        )
    if provider_id == "local":
        return local_order(
            ensure_provider_fn,
            configs,
            list_providers_fn,
            provider_toml=provider_toml,
            logger=logger,
        )
    canonical_id = canonical_provider_id_fn(provider_id)
    if canonical_id and canonical_id in configs:
        return [canonical_id]
    return []


def _is_canary_attempt(
    ensure_provider_fn,
    provider_id: str,
    model: Optional[str],
) -> bool:
    _ = model
    current_provider = ensure_provider_fn(provider_id)
    if current_provider is None:
        return False
    return current_provider.soft_open_probe_available()


def top_providers_for(
    list_providers_fn,
    is_configured_fn,
    local_order_fn,
    cheapest_order_fn,
    capability: str,
    *,
    prefer_local: bool = False,
    prefer_cost: bool = False,
    limit: int = 6,
) -> List[str]:
    cap = capability.strip().lower()
    providers = list_providers_fn(include_hidden=False)
    candidates = [
        item["id"]
        for item in providers
        if cap in {c.lower() for c in item["capabilities"]} and is_configured_fn(item["id"])
    ]
    if prefer_local:
        local_candidates = [p for p in local_order_fn() if p in candidates]
        candidates = local_candidates
    elif prefer_cost:
        ranked = cheapest_order_fn()
        candidates = [p for p in ranked if p in candidates]
    return candidates[: max(1, limit)]
