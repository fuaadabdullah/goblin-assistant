"""Pluggable candidate-ranking strategies for provider dispatch."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Dict, Protocol

from api.routing.router import cost_router, hybrid_router

ProviderCosts = Dict[str, tuple[float, float]]


class CandidateRouter(Protocol):
    def rank(
        self,
        candidates: Sequence[str],
        provider_costs: ProviderCosts,
    ) -> list[str]:
        ...


class CheapestRouter:
    def rank(
        self,
        candidates: Sequence[str],
        provider_costs: ProviderCosts,
    ) -> list[str]:
        return cost_router.rank(list(candidates), provider_costs)


class HybridRouter:
    def rank(
        self,
        candidates: Sequence[str],
        provider_costs: ProviderCosts,
    ) -> list[str]:
        return hybrid_router.rank(list(candidates), provider_costs)


class LocalRouter:
    def rank(
        self,
        candidates: Sequence[str],
        provider_costs: ProviderCosts,
    ) -> list[str]:
        del provider_costs
        return list(candidates)


class DirectRouter:
    def rank(
        self,
        candidates: Sequence[str],
        provider_costs: ProviderCosts,
    ) -> list[str]:
        del provider_costs
        return list(candidates[:1])


def rank_cheapest(
    candidates: Sequence[str],
    provider_costs: ProviderCosts,
) -> list[str]:
    return CheapestRouter().rank(candidates, provider_costs)


def rank_hybrid(
    candidates: Sequence[str],
    provider_costs: ProviderCosts,
) -> list[str]:
    return HybridRouter().rank(candidates, provider_costs)


def rank_local(candidates: Sequence[str]) -> list[str]:
    return LocalRouter().rank(candidates, {})
