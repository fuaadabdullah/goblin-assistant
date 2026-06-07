"""Routing strategies and runtime statistics for provider selection.

Implementation is split across focused sub-modules:
  router_store.py          — SQLite persistence (RoutingRegistryStore, ProviderStats)
  router_supabase.py       — Supabase mirror / restore helpers
  router_registry.py       — In-memory RoutingRegistry + registry singleton
  router_strategies.py     — LatencyRouter, CostRouter, HybridRouter, ModelTierRouter
  router_orchestration.py  — top_providers_for, route_task, route_task_sync

All names that external code imports from this module are re-exported below so
no callers need to change.
"""

from .router_orchestration import route_task, route_task_sync, top_providers_for
from .router_registry import RoutingRegistry, registry
from .router_store import ProviderStats, RoutingRegistryStore
from .router_strategies import (
    CostRouter,
    HybridRouter,
    LatencyRouter,
    ModelTierRouter,
    cost_router,
    hybrid_router,
    latency_router,
    tier_router,
)

__all__ = [
    # data / persistence
    "ProviderStats",
    "RoutingRegistryStore",
    # registry
    "RoutingRegistry",
    "registry",
    # strategy classes
    "LatencyRouter",
    "CostRouter",
    "HybridRouter",
    "ModelTierRouter",
    # strategy singletons
    "latency_router",
    "cost_router",
    "hybrid_router",
    "tier_router",
    # routing functions
    "top_providers_for",
    "route_task",
    "route_task_sync",
]
