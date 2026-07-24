"""Routing strategy implementations: latency, cost, hybrid, and model-tier."""

from __future__ import annotations

import importlib
import os
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import structlog

from .router_registry import registry as default_registry

logger = structlog.get_logger()

_TIERS_PATH = Path(__file__).resolve().parents[5] / "config" / "routing_tiers.toml"


def _parse_toml(path: Path) -> Dict[str, object]:
    try:
        import tomllib

        with open(path, "rb") as f:
            return tomllib.load(f)
    except ImportError:
        toml = importlib.import_module("toml")
        with open(path, "r", encoding="utf-8") as f:
            return toml.load(f)


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
    """Performance/cost tier -> provider/model lookup.

    TIER_PROVIDERS/TIER_MODELS remain as class-level defaults (used by
    routing/evaluation.py's benchmark harness as a stable baseline, and as
    the fallback if config/routing_tiers.toml is missing or fails to parse).
    providers_for_tier()/model_for_provider() prefer the TOML — administrators
    can edit tier composition there without touching router code.
    """

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

    def __init__(self) -> None:
        self._tier_models: Dict[str, Dict[str, str]] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._tier_models = self._load_tier_models()
            self._loaded = True

    def reload(self) -> None:
        """Force a re-read of routing_tiers.toml (e.g. after an admin edit)."""
        self._tier_models = self._load_tier_models()
        self._loaded = True

    def _load_tier_models(self) -> Dict[str, Dict[str, str]]:
        if not _TIERS_PATH.exists():
            return self.TIER_MODELS
        try:
            parsed = _parse_toml(_TIERS_PATH)
        except Exception as exc:
            logger.warning("routing_tiers_load_failed", error=str(exc))
            return self.TIER_MODELS
        tiers = parsed.get("tiers")
        if not isinstance(tiers, dict) or not tiers:
            return self.TIER_MODELS
        return {
            str(tier_name): {str(pid): str(model) for pid, model in providers.items()}
            for tier_name, providers in tiers.items()
            if isinstance(providers, dict)
        }

    def providers_for_tier(self, tier: str) -> List[str]:
        self._ensure_loaded()
        models = self._tier_models.get(tier) or self._tier_models.get("smart", {})
        return list(models.keys())

    def model_for_provider(self, tier: str, provider_id: str) -> Optional[str]:
        self._ensure_loaded()
        return self._tier_models.get(tier, {}).get(provider_id)


latency_router = LatencyRouter()
cost_router = CostRouter()
hybrid_router = HybridRouter(cost_weight=float(os.getenv("ROUTING_COST_WEIGHT", "0.35")))
tier_router = ModelTierRouter()
