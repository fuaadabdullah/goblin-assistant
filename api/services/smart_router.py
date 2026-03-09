"""
Compatibility smart-router facade backed by the authoritative dispatcher.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .provider_health import health_monitor
from api.providers.dispatcher import canonical_provider_id, dispatcher
from api.routing.router import (
    cost_router,
    hybrid_router,
    latency_router,
    registry,
    tier_router,
    top_providers_for,
)


class TaskType(Enum):
    CHAT = "chat"
    CODE_GENERATION = "code"
    CODE_REVIEW = "code_review"
    REASONING = "reasoning"
    SUMMARIZATION = "summary"
    EMBEDDING = "embedding"
    IMAGE_GENERATION = "image"
    VISION = "vision"
    TRANSLATION = "translation"


class RoutingStrategy(Enum):
    COST_OPTIMIZED = "cost_optimized"
    QUALITY_FIRST = "quality_first"
    LATENCY_OPTIMIZED = "latency_optimized"
    BALANCED = "balanced"
    LOCAL_FIRST = "local_first"


@dataclass
class ProviderCost:
    input_cost: float
    output_cost: float

    def estimate(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens / 1000 * self.input_cost
            + output_tokens / 1000 * self.output_cost
        )


@dataclass
class ProviderSelection:
    provider_id: str
    model: str
    reason: str
    fallback_chain: List[str]
    estimated_cost: float
    expected_latency_ms: float


class CostTracker:
    def __init__(self, hourly_budget: float = 10.0) -> None:
        self.hourly_budget = hourly_budget
        self.current_hour_spend = 0.0
        self.hour_start = datetime.now(timezone.utc).replace(
            minute=0, second=0, microsecond=0
        )
        self.request_history: List[Dict[str, Any]] = []

    def _reset_if_new_hour(self) -> None:
        current_hour = datetime.now(timezone.utc).replace(
            minute=0, second=0, microsecond=0
        )
        if current_hour > self.hour_start:
            self.hour_start = current_hour
            self.current_hour_spend = 0.0
            self.request_history = []

    def estimate_cost(self, provider_id: str, estimated_tokens: int = 500) -> float:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        try:
            provider = dispatcher.get_provider(canonical_id)
        except KeyError:
            return 0.0
        return provider.estimate_cost(estimated_tokens, estimated_tokens)

    def record_request(
        self,
        provider_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        self._reset_if_new_hour()
        cost = self.estimate_cost(provider_id, estimated_tokens=0)
        canonical_id = canonical_provider_id(provider_id) or provider_id
        try:
            provider = dispatcher.get_provider(canonical_id)
            cost = provider.estimate_cost(input_tokens, output_tokens)
        except KeyError:
            cost = 0.0
        self.current_hour_spend += cost
        self.request_history.append(
            {
                "provider": canonical_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def budget_remaining(self) -> float:
        self._reset_if_new_hour()
        return max(0.0, self.hourly_budget - self.current_hour_spend)

    def should_use_cheaper_provider(self) -> bool:
        self._reset_if_new_hour()
        return self.current_hour_spend > (self.hourly_budget * 0.7)

    def get_status(self) -> Dict[str, Any]:
        self._reset_if_new_hour()
        return {
            "hourly_budget": self.hourly_budget,
            "current_spend": round(self.current_hour_spend, 4),
            "remaining": round(self.budget_remaining(), 4),
            "hour_start": self.hour_start.isoformat(),
            "request_count": len(self.request_history),
            "should_use_cheaper": self.should_use_cheaper_provider(),
        }


class SmartRouter:
    def __init__(
        self,
        strategy: RoutingStrategy = RoutingStrategy.COST_OPTIMIZED,
        hourly_budget: float = 10.0,
    ) -> None:
        self.strategy = strategy
        self.cost_tracker = CostTracker(hourly_budget)

    def _model_for_provider(self, provider_id: str) -> str:
        config = dispatcher.get_provider_config(provider_id)
        return str(config.get("default_model", "")) or dispatcher.get_provider(provider_id).default_model

    def _build_emergency_selection(self) -> ProviderSelection:
        return ProviderSelection(
            provider_id="mock",
            model="mock-gpt",
            reason="No providers available - using mock",
            fallback_chain=[],
            estimated_cost=0.0,
            expected_latency_ms=0.0,
        )

    def _ordered_candidates(
        self,
        strategy: RoutingStrategy,
        capability: str,
    ) -> List[str]:
        candidates = top_providers_for(capability, limit=20)
        if not candidates:
            return []

        provider_costs = {
            provider_id: (
                dispatcher.get_provider(provider_id).COST_INPUT_PER_1K,
                dispatcher.get_provider(provider_id).COST_OUTPUT_PER_1K,
            )
            for provider_id in candidates
        }

        if strategy == RoutingStrategy.COST_OPTIMIZED:
            return cost_router.rank(candidates, provider_costs)
        if strategy == RoutingStrategy.LOCAL_FIRST:
            local_candidates = [
                provider_id
                for provider_id in tier_router.providers_for_tier("local")
                if provider_id in candidates
            ]
            return local_candidates or candidates
        if strategy == RoutingStrategy.LATENCY_OPTIMIZED:
            return latency_router.rank(candidates, provider_costs)
        if strategy == RoutingStrategy.BALANCED:
            return hybrid_router.rank(candidates, provider_costs)

        quality_order = ["anthropic", "openai", "azure_openai", "vertex_ai", "gemini"]
        prioritized = [provider_id for provider_id in quality_order if provider_id in candidates]
        leftovers = [provider_id for provider_id in candidates if provider_id not in prioritized]
        return prioritized + leftovers

    def select_provider(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        strategy: Optional[RoutingStrategy] = None,
        preferred_provider: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> ProviderSelection:
        del messages
        active_strategy = strategy or self.strategy
        capability = task_type or TaskType.CHAT.value

        if preferred_provider:
            canonical_id = canonical_provider_id(preferred_provider) or preferred_provider
            if health_monitor.is_available(canonical_id):
                model = self._model_for_provider(canonical_id)
                return ProviderSelection(
                    provider_id=canonical_id,
                    model=model,
                    reason="Preferred provider selected",
                    fallback_chain=[],
                    estimated_cost=self.cost_tracker.estimate_cost(canonical_id),
                    expected_latency_ms=health_monitor.get_latency(canonical_id),
                )

        ordered = self._ordered_candidates(active_strategy, capability)
        if not ordered:
            return self._build_emergency_selection()

        selected = ordered[0]
        return ProviderSelection(
            provider_id=selected,
            model=self._model_for_provider(selected),
            reason=f"Selected via {active_strategy.value}",
            fallback_chain=ordered[1:],
            estimated_cost=self.cost_tracker.estimate_cost(selected),
            expected_latency_ms=health_monitor.get_latency(selected),
        )

    async def invoke_with_fallback(
        self,
        invoke_fn,
        messages: List[Dict[str, Any]],
        strategy: Optional[RoutingStrategy] = None,
        preferred_provider: Optional[str] = None,
        timeout_ms: int = 30_000,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        payload = dict(kwargs.get("payload") or {})
        payload.setdefault("messages", messages)

        selection = self.select_provider(
            messages=messages,
            strategy=strategy,
            preferred_provider=preferred_provider,
            task_type=kwargs.get("task_type"),
        )
        tried: List[str] = []
        for provider_id in [selection.provider_id, *selection.fallback_chain]:
            tried.append(provider_id)
            model = self._model_for_provider(provider_id)
            try:
                result = await invoke_fn(provider_id, model, payload, timeout_ms)
            except Exception:
                registry.record_failure(provider_id)
                continue

            if isinstance(result, dict) and result.get("ok"):
                usage = {}
                if isinstance(result.get("result"), dict):
                    usage = result["result"].get("usage") or {}
                if not usage and isinstance(result.get("usage"), dict):
                    usage = result["usage"]
                self.cost_tracker.record_request(
                    provider_id,
                    int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
                    int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
                )
                result.setdefault(
                    "routing",
                    {"provider": provider_id, "tried_providers": tried},
                )
                return result

        return {
            "ok": False,
            "error": "all providers failed",
            "routing": {"provider": "none", "tried_providers": tried},
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "healthy_providers": health_monitor.get_healthy_providers(),
            "available_providers": health_monitor.get_available_providers(),
            "best_providers": health_monitor.get_best_providers(),
            "routing_registry": registry.snapshot(),
            "cost_tracking": self.cost_tracker.get_status(),
        }


smart_router = SmartRouter(strategy=RoutingStrategy.COST_OPTIMIZED)


def get_smart_router() -> SmartRouter:
    return smart_router
