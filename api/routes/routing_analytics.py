"""Routing analytics endpoints backed by the authoritative routing stack."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Any, Dict

from api.providers.dispatcher import dispatcher
from api.routing.router import registry
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


@router.get("/providers")
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
