"""Routing strategy implementations: latency, cost, hybrid, and model-tier."""

from __future__ import annotations

import os
import sys
import uuid
from typing import Dict, List, Optional

import structlog

from .router_registry import registry as default_registry

logger = structlog.get_logger()


def _get_registry():
    router_module = sys.modules.get("api.routing.router")
    if router_module is not None:
        module_registry = getattr(router_module, "registry", None)
        if module_registry is not None:
            return module_registry
    return default_registry


class LatencyRouter:
    def rank(
        self,
        candidates: List[str],
        provider_costs: Dict[str, tuple[float, float]],
    ) -> List[str]:
        del provider_costs

        def score(provider_id: str) -> float:
            stats = _get_registry().get(provider_id)
            reliability = max(stats.success_rate, 0.01)
            return stats.ewma_latency_ms / reliability

        return sorted(candidates, key=score)


class CostRouter:
    def rank(
        self,
        candidates: List[str],
        provider_costs: Dict[str, tuple[float, float]],
    ) -> List[str]:
        def cost_score(provider_id: str) -> float:
            input_cost, output_cost = provider_costs.get(provider_id, (0.0, 0.0))
            return input_cost + output_cost

        return sorted(candidates, key=cost_score)


class HybridRouter:
    def __init__(self, cost_weight: float = 0.35) -> None:
        self.cost_weight = max(0.0, min(1.0, cost_weight))

    def rank(
        self,
        candidates: List[str],
        provider_costs: Dict[str, tuple[float, float]],
        *,
        request_id: Optional[str] = None,
    ) -> List[str]:
        if not candidates:
            return []

        req_id = request_id or str(uuid.uuid4())

        routing_registry = _get_registry()
        latencies = {pid: routing_registry.get(pid).ewma_latency_ms for pid in candidates}
        costs = {pid: sum(provider_costs.get(pid, (0.0, 0.0))) for pid in candidates}
        max_latency = max(latencies.values()) or 1.0
        max_cost = max(costs.values()) or 1.0

        breakdown: Dict[str, Dict[str, float]] = {}

        def score(provider_id: str) -> float:
            stats = routing_registry.get(provider_id)
            normalized_latency = latencies[provider_id] / max_latency
            normalized_cost = costs[provider_id] / max_cost if max_cost else 0.0
            reliability = max(stats.success_rate, 0.1)
            final = (
                (1 - self.cost_weight) * normalized_latency + self.cost_weight * normalized_cost
            ) / reliability
            breakdown[provider_id] = {
                "normalized_latency": round(normalized_latency, 4),
                "normalized_cost": round(normalized_cost, 4),
                "reliability": round(reliability, 4),
                "final_score": round(final, 6),
            }
            return final

        ranked = sorted(candidates, key=score)

        logger.info(
            "routing_decision",
            request_id=req_id,
            cost_weight=self.cost_weight,
            candidates=candidates,
            rank_order=ranked,
            score_breakdown=breakdown,
        )
        routing_registry.log_decision(
            request_id=req_id,
            cost_weight=self.cost_weight,
            candidates=candidates,
            score_breakdown=breakdown,
            rank_order=ranked,
        )

        return ranked


class ModelTierRouter:
    TIER_PROVIDERS: Dict[str, List[str]] = {
        "fast": ["groq", "siliconeflow", "gemini"],
        "smart": ["openai", "anthropic", "deepseek", "aliyun"],
        "best": ["openai", "anthropic", "gcp_vllm", "azure_openai"],
        "local": ["gcp_vm", "ollama_local", "aliyun"],
    }

    TIER_MODELS: Dict[str, Dict[str, str]] = {
        "fast": {
            "groq": "llama-3.3-70b-versatile",
            "siliconeflow": "Qwen/Qwen2.5-7B-Instruct",
            "gemini": "gemini-2.0-flash",
        },
        "smart": {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-haiku-latest",
            "deepseek": "deepseek-chat",
            "aliyun": "qwen-plus",
        },
        "best": {
            "openai": "gpt-4o",
            "anthropic": "claude-sonnet-4-20250514",
            "gcp_vllm": "qwen3-32b",
            "azure_openai": "gpt-4o",
        },
        "local": {
            "gcp_vm": "gemini-2.5-flash",
            "ollama_local": "qwen2.5:3b",
            "aliyun": "qwen-plus",
        },
    }

    def providers_for_tier(self, tier: str) -> List[str]:
        return list(self.TIER_PROVIDERS.get(tier, self.TIER_PROVIDERS["smart"]))

    def model_for_provider(self, tier: str, provider_id: str) -> Optional[str]:
        return self.TIER_MODELS.get(tier, {}).get(provider_id)


latency_router = LatencyRouter()
cost_router = CostRouter()
hybrid_router = HybridRouter(cost_weight=float(os.getenv("ROUTING_COST_WEIGHT", "0.35")))
tier_router = ModelTierRouter()
