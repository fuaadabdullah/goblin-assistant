"""Debug introspection and snapshot building."""

from __future__ import annotations

from typing import Any, Dict, List


def build_debug_info(
    dispatcher: Any,
    *,
    model_aliases: Dict[str, tuple[str, str]],
    model_alias_patterns: List[tuple[Any, str, str]],
    provider_aliases: Dict[str, str],
    visible_provider_ids: List[str],
) -> Dict[str, Any]:
    """Build a complete debug snapshot of routing state and configuration.

    Includes routing table, registry stats, budget status, warmup states,
    and all alias mappings.
    """
    from ...routing.router import registry

    routing_table = [
        {
            "provider_id": item["id"],
            "name": item["name"],
            "priority_tier": item["priority_tier"],
            "tier": item["tier"],
            "local_routing": item["local_routing"],
            "configured": dispatcher.is_configured(item["id"]),
            "instantiated": item["id"] in dispatcher._providers,
            "circuit_breaker": (
                dispatcher._providers[item["id"]].circuit_status()
                if item["id"] in dispatcher._providers
                else {}
            ),
            "hidden": item["hidden"],
            "capabilities": item["capabilities"],
            "default_model": item["default_model"],
            "warmup": dispatcher._warmup_state_for(item["id"]),
        }
        for item in dispatcher.list_providers(include_hidden=True)
    ]

    return {
        "routing_table": routing_table,
        "registry_stats": registry.snapshot(),
        "registry_metrics": registry.metrics_snapshot(),
        "registry_persisted_snapshot": registry.persisted_snapshot(),
        "registry_persistence": registry.persistence_status(),
        "budget_status": dispatcher._budget_status(),
        "warmup_states": dict(dispatcher._warmup_states),
        "routing_min_success_rate": dispatcher._routing_min_success_rate,
        "circuit_canary_percent": dispatcher._circuit_canary_percent,
        "model_aliases": {k: list(v) for k, v in model_aliases.items()},
        "model_alias_patterns": [pattern.pattern for pattern, _, _ in model_alias_patterns],
        "provider_aliases": dict(provider_aliases),
        "visible_provider_order": list(visible_provider_ids),
    }
