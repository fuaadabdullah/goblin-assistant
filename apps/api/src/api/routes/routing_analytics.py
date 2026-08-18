"""Routing analytics endpoints backed by the authoritative routing stack."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from api.providers.dispatcher import dispatcher
from api.routing.provider_selection import get_recent_explanations
from api.routing.router import hybrid_router, registry
from api.services.provider_health import health_monitor
from api.services.smart_router import RoutingStrategy, smart_router

router = APIRouter(prefix="/routing", tags=["routing-analytics"])


@router.get("/health")
async def get_provider_health() -> Dict[str, Any]:
    await health_monitor.refresh(include_hidden=False)
    return {
        "available": True,
        "providers": health_monitor.get_all_status(),
        "healthy_providers": health_monitor.get_healthy_providers(),
        "best_providers": health_monitor.get_best_providers(),
    }


@router.get("/health/{provider_id}")
async def get_provider_health_detail(provider_id: str) -> Dict[str, Any]:
    await health_monitor.probe_provider(provider_id)
    status = health_monitor.get_status(provider_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    return status


@router.get("/costs")
async def get_cost_tracking() -> Dict[str, Any]:
    return {"available": True, **smart_router.cost_tracker.get_status()}


@router.get("/status")
async def get_routing_status() -> Dict[str, Any]:
    await health_monitor.refresh(include_hidden=False)
    return {
        "available": True,
        **smart_router.get_status(),
        "providers": await dispatcher.get_provider_inventory(include_hidden=False),
    }


@router.get("/strategies")
async def list_routing_strategies() -> Dict[str, Any]:
    return {
        "strategies": [
            {
                "id": RoutingStrategy.COST_OPTIMIZED.value,
                "name": "Cost Optimized",
                "description": "Prioritize the cheapest healthy providers.",
            },
            {
                "id": RoutingStrategy.QUALITY_FIRST.value,
                "name": "Quality First",
                "description": "Prioritize the strongest cloud providers.",
            },
            {
                "id": RoutingStrategy.LATENCY_OPTIMIZED.value,
                "name": "Latency Optimized",
                "description": "Prioritize providers with the best EWMA latency.",
            },
            {
                "id": RoutingStrategy.LOCAL_FIRST.value,
                "name": "Local First",
                "description": "Prioritize self-hosted and private routing tiers.",
            },
            {
                "id": RoutingStrategy.BALANCED.value,
                "name": "Balanced",
                "description": "Blend cost and latency scores.",
            },
        ],
        "default": smart_router.strategy.value,
    }


@router.get("/providers/analytics")
async def list_available_providers() -> Dict[str, Any]:
    await health_monitor.refresh(include_hidden=False)
    inventory = await dispatcher.get_provider_inventory(include_hidden=False)
    return {
        "providers": {
            entry["id"]: {
                "name": entry["name"],
                "type": entry["tier"],
                "capabilities": entry["capabilities"],
                "models": entry["models"],
                "health": health_monitor.get_status(entry["id"]),
                "routing_stats": registry.snapshot().get(entry["id"], {}),
            }
            for entry in inventory
        }
    }


@router.post("/test/{provider_id}")
async def test_provider(provider_id: str) -> Dict[str, Any]:
    status = await health_monitor.probe_provider(provider_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    return status


@router.get("/audit")
async def get_routing_audit(limit: int = 200) -> Dict[str, Any]:
    """Return the most recent routing decision + outcome audit records."""
    clamped = max(1, min(limit, 1000))
    return {
        "records": registry.get_audit_trail(limit=clamped),
        "count": len(registry.get_audit_trail(limit=clamped)),
        "current_cost_weight": hybrid_router.cost_weight,
    }


@router.get("/observability")
async def get_routing_observability(limit: int = 100) -> Dict[str, Any]:
    """Dashboard-ready routing observability snapshot."""
    clamped = max(1, min(limit, 500))
    await health_monitor.refresh(include_hidden=False)

    recent_decisions = get_recent_explanations(limit=clamped)
    audit_records = registry.get_audit_trail(limit=clamped)
    registry_metrics = registry.metrics_snapshot()
    health = health_monitor.get_all_status()

    return {
        "available": True,
        "routing_waterfall": _routing_waterfall(recent_decisions),
        "provider_timelines": _provider_timelines(recent_decisions, audit_records),
        "cost_dashboard": _cost_dashboard(registry_metrics, recent_decisions),
        "selection_reasons": [
            {
                "routing_id": item["routing_id"],
                "chosen_provider": item.get("chosen_provider"),
                "reason": item.get("selection_reason"),
                "ml_confidence": item.get("ml_confidence", {}),
            }
            for item in recent_decisions
        ],
        "fallback_reasons": [
            {
                "routing_id": item["routing_id"],
                "reasons": item.get("fallback_reasons", []),
            }
            for item in recent_decisions
        ],
        "prompt_classification": [
            {
                "routing_id": item["routing_id"],
                **dict(item.get("prompt_classification", {})),
            }
            for item in recent_decisions
        ],
        "ml_confidence": [
            {
                "routing_id": item["routing_id"],
                **dict(item.get("ml_confidence", {})),
            }
            for item in recent_decisions
        ],
        "latency_percentiles": _latency_percentiles(registry_metrics, health),
        "recent_decisions": recent_decisions,
        "audit": audit_records,
    }


@router.get("/weight")
async def get_routing_weight() -> Dict[str, Any]:
    """Return the current HybridRouter cost/latency weight split."""
    return {
        "cost_weight": hybrid_router.cost_weight,
        "latency_weight": round(1.0 - hybrid_router.cost_weight, 4),
        "source": "ROUTING_COST_WEIGHT env var (default 0.35)",
    }


def _routing_waterfall(recent_decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
    stage_totals: Dict[str, Dict[str, float]] = {}
    for decision in recent_decisions:
        for stage in decision.get("routing_waterfall", []):
            name = str(stage.get("stage") or "unknown")
            duration = max(0.0, float(stage.get("duration_ms") or 0.0))
            bucket = stage_totals.setdefault(name, {"count": 0.0, "total_ms": 0.0, "max_ms": 0.0})
            bucket["count"] += 1.0
            bucket["total_ms"] += duration
            bucket["max_ms"] = max(bucket["max_ms"], duration)

    return {
        "recent": [
            {
                "routing_id": decision["routing_id"],
                "chosen_provider": decision.get("chosen_provider"),
                "stages": decision.get("routing_waterfall", []),
                "total_duration_ms": round(
                    sum(
                        float(stage.get("duration_ms") or 0.0)
                        for stage in decision.get("routing_waterfall", [])
                    ),
                    4,
                ),
            }
            for decision in recent_decisions
        ],
        "stage_summary": {
            stage: {
                "count": int(values["count"]),
                "avg_ms": round(values["total_ms"] / values["count"], 4)
                if values["count"]
                else 0.0,
                "max_ms": round(values["max_ms"], 4),
            }
            for stage, values in stage_totals.items()
        },
    }


def _provider_timelines(
    recent_decisions: List[Dict[str, Any]],
    audit_records: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    timelines: Dict[str, List[Dict[str, Any]]] = {}

    for decision in recent_decisions:
        routing_id = decision["routing_id"]
        created_at = decision.get("created_at")
        chosen = decision.get("chosen_provider")
        for candidate in decision.get("candidates", []):
            provider_id = str(candidate.get("provider_id") or "")
            if not provider_id:
                continue
            event = {
                "event": "selected" if provider_id == chosen else "ranked_fallback",
                "routing_id": routing_id,
                "timestamp": created_at,
                "task_type": decision.get("task_type"),
                "pct": candidate.get("pct"),
                "score": candidate.get("score"),
            }
            if provider_id != chosen:
                event["fallback_reason"] = next(
                    (
                        reason.get("reason")
                        for reason in decision.get("fallback_reasons", [])
                        if reason.get("provider_id") == provider_id
                    ),
                    "ranked_below_selected_provider",
                )
            timelines.setdefault(provider_id, []).append(event)

    for record in audit_records:
        provider_id = str(record.get("provider_id") or "")
        if not provider_id:
            continue
        timelines.setdefault(provider_id, []).append(
            {
                "event": record.get("event", "audit"),
                "request_id": record.get("request_id"),
                "timestamp": record.get("timestamp"),
                "selected_model": record.get("selected_model"),
                "actual_latency_ms": record.get("actual_latency_ms"),
                "actual_cost_usd": record.get("actual_cost_usd"),
                "latency_ms": record.get("latency_ms"),
                "cost_usd": record.get("cost_usd"),
                "visible_outcome": record.get("visible_outcome"),
                "failure_class": record.get("failure_class") or record.get("error_category"),
                "fallback_reason": record.get("fallback_reason"),
                "alternatives_considered": record.get("alternatives_considered"),
                "context_sources": record.get("context_sources"),
                "tool_usage": record.get("tool_usage"),
            }
        )

    return {
        provider_id: sorted(
            events,
            key=lambda item: float(item.get("timestamp") or 0.0),
            reverse=True,
        )
        for provider_id, events in timelines.items()
    }


def _cost_dashboard(
    registry_metrics: Dict[str, Any],
    recent_decisions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    providers = registry_metrics.get("providers", {})
    return {
        "current_hour_bucket": registry_metrics.get("current_hour_bucket"),
        "current_hour_spend": registry_metrics.get("current_hour_spend", {}),
        "current_hour_spend_total": registry_metrics.get("current_hour_spend_total", 0.0),
        "provider_totals": {
            provider_id: {
                "total_cost_usd": metrics.get("total_cost_usd", 0.0),
                "success_rate": metrics.get("success_rate", 0.0),
                "ewma_tokens_per_sec": metrics.get("ewma_tokens_per_sec", 0.0),
            }
            for provider_id, metrics in providers.items()
        },
        "recent_selected_provider_counts": _selected_provider_counts(recent_decisions),
    }


def _selected_provider_counts(recent_decisions: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for decision in recent_decisions:
        provider_id = decision.get("chosen_provider")
        if provider_id:
            counts[str(provider_id)] = counts.get(str(provider_id), 0) + 1
    return counts


def _latency_percentiles(
    registry_metrics: Dict[str, Any],
    health: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    providers: Dict[str, Any] = {}
    for provider_id, metrics in registry_metrics.get("providers", {}).items():
        providers.setdefault(provider_id, {})["dispatch"] = {
            "ewma_latency_ms": metrics.get("ewma_latency_ms"),
            "latency_percentiles_ms": metrics.get("latency_percentiles_ms", {}),
            "latency_sample_count": metrics.get("latency_sample_count", 0),
        }
    for provider_id, status in health.items():
        providers.setdefault(provider_id, {})["health_probe"] = {
            "avg_latency_ms": status.get("avg_latency_ms"),
            "latency_percentiles_ms": status.get("latency_percentiles_ms", {}),
            "latency_sample_count": status.get("latency_sample_count", 0),
        }
    return {"providers": providers}
