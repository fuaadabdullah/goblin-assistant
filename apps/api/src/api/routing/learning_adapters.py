"""Routing-owned adapters for learned routing state.

Services use this module instead of importing route/controller modules such as
``ml_router`` and ``feature_router`` directly.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def rank_with_bandit_router(
    candidates: List[str],
    provider_costs: Dict[str, tuple],
    *,
    task_type: str,
    request_id: Optional[str] = None,
    request: Optional[object] = None,
) -> List[str]:
    from api.routing.ml_router import bandit_router

    return bandit_router.rank(
        candidates,
        provider_costs,
        task_type=task_type,
        request_id=request_id,
        request=request,
    )


def rank_prompt_with_bandit_router(
    candidates: List[str],
    provider_costs: Dict[str, tuple],
    *,
    task_type: str,
    prompt: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    intent_label: str = "unknown",
    intent_confidence: float = 0.0,
    request_id: Optional[str] = None,
) -> List[str]:
    from api.routing.ml_router import bandit_cache
    from api.routing.routing_pipeline import build_routing_pipeline

    result = build_routing_pipeline(bandit_cache=bandit_cache).route_prompt(
        candidates,
        prompt,
        conversation_history=conversation_history or [],
        task_type=task_type,
        intent_label=intent_label,
        intent_confidence=intent_confidence,
        provider_costs=provider_costs,
        routing_id=request_id or "",
        prefer_supplied_task_type=True,
    )
    return [score.provider_id for score in result.scores]


def record_bandit_outcome(
    *,
    request_id: str,
    task_type: str,
    provider_id: str,
    was_selected: bool,
    latency_ms: float,
    cost_usd: float,
    success: bool,
) -> None:
    from api.routing.ml_router import bandit_router

    bandit_router.record_outcome(
        request_id=request_id,
        task_type=task_type,
        provider_id=provider_id,
        was_selected=was_selected,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        success=success,
    )


def apply_bandit_feedback(
    *,
    task_type: str,
    provider_id: str,
    success: Optional[bool],
    rating: Optional[int],
) -> None:
    from api.routing.ml_router import _fire_bandit_state_upsert, bandit_cache

    updated = bandit_cache.update(
        task_type,
        provider_id,
        success=success,
        rating=rating,
    )
    _fire_bandit_state_upsert(updated)


def apply_feature_router_feedback(
    *,
    task_type: str,
    provider_id: str,
    success: bool,
    rating: Optional[int],
    complexity_score: Optional[float] = None,
    intent_label: Optional[str] = None,
) -> None:
    from api.routing.feature_extractor import (
        ProviderFeatures,
        RoutingFeatures,
        feature_extractor,
    )
    from api.routing.feature_router import feature_router
    from api.routing.router_registry import registry

    request_features = RoutingFeatures(
        prompt_length_bucket=1,
        task_type=task_type,
        complexity_score=float(complexity_score or 0.5),
        conversation_turn=0,
        intent_label=intent_label or task_type or "unknown",
        intent_confidence=0.7,
    )

    snapshot = registry.snapshot()
    pf_map = feature_extractor.extract_providers(
        [provider_id],
        {provider_id: (0.0, 0.0)},
        snapshot,
    )
    provider_features = pf_map.get(
        provider_id,
        ProviderFeatures(
            provider_id=provider_id,
            success_rate=0.5,
            norm_latency=0.5,
            norm_cost=0.5,
            is_healthy=True,
        ),
    )

    feature_router.record_outcome(
        task_type=task_type,
        request=request_features,
        provider_id=provider_id,
        provider_features=provider_features,
        success=success,
        rating=rating,
    )
