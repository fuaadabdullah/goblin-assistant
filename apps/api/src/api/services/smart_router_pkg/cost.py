"""Cost tracking helpers for the smart-router facade."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from api.providers.dispatcher import canonical_provider_id, dispatcher
from api.providers.pricing import resolve_model_pricing

from .types import ProviderCost


def provider_pricing(provider: Any) -> ProviderCost:
    config = getattr(provider, "config", None)
    if isinstance(config, dict):
        pricing = resolve_model_pricing(
            getattr(provider, "provider_id", ""),
            getattr(provider, "default_model", None) or None,
            config=config,
        )
        return ProviderCost(input_cost=pricing.input_per1k, output_cost=pricing.output_per1k)

    return ProviderCost(input_cost=0.0, output_cost=0.0)


class CostTracker:
    def __init__(self, hourly_budget: float = 10.0) -> None:
        self.hourly_budget = hourly_budget
        self.current_hour_spend = 0.0
        self.hour_start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        self.request_history: List[Dict[str, Any]] = []

    def _reset_if_new_hour(self) -> None:
        current_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
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
        pricing = provider_pricing(provider)
        return pricing.estimate(estimated_tokens, estimated_tokens)

    def record_request(
        self,
        provider_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        self._reset_if_new_hour()
        canonical_id = canonical_provider_id(provider_id) or provider_id
        try:
            provider = dispatcher.get_provider(canonical_id)
            pricing = provider_pricing(provider)
            cost = pricing.estimate(input_tokens, output_tokens)
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
