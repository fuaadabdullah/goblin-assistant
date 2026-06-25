"""Public routing façade.

The implementation lives in focused modules:
  selection.py       - top_providers_for, route_task, route_task_sync
  policy_engine.py    - LatencyRouter, CostRouter, HybridRouter, ModelTierRouter
  registry_store.py   - ProviderStats, RoutingRegistryStore
  router_registry.py  - RoutingRegistry + registry singleton

This module re-exports the routing surface for compatibility and keeps the
package entrypoint router-first.
"""

from .policy_engine import (
    CostRouter,
    HybridRouter,
    LatencyRouter,
    ModelTierRouter,
    cost_router,
    hybrid_router,
    latency_router,
    tier_router,
)
from .registry_store import ProviderStats, RoutingRegistryStore
from .router_registry import RoutingRegistry, registry
from .selection import route_task, route_task_sync, top_providers_for

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
