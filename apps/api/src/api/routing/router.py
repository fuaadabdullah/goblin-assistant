"""Routing strategies and runtime statistics for provider selection."""

from __future__ import annotations

import asyncio
import collections
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()


@dataclass
class ProviderStats:
    provider_id: str
    ewma_latency_ms: float = 5000.0
    ewma_alpha: float = 0.2
    success_count: int = 0
    failure_count: int = 0
    total_cost_usd: float = 0.0
    last_used: float = field(default_factory=time.time)

    def update_latency(self, latency_ms: float) -> None:
        self.ewma_latency_ms = (
            self.ewma_alpha * latency_ms
            + (1 - self.ewma_alpha) * self.ewma_latency_ms
        )

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 1.0


class RoutingRegistry:
    _AUDIT_MAX = 1000  # ring buffer capacity for decision audit trail

    def __init__(self) -> None:
        self._stats: Dict[str, ProviderStats] = {}
        self._decision_log: collections.deque = collections.deque(maxlen=self._AUDIT_MAX)

    def get(self, provider_id: str) -> ProviderStats:
        if provider_id not in self._stats:
            self._stats[provider_id] = ProviderStats(provider_id=provider_id)
        return self._stats[provider_id]

    def record_success(
        self,
        provider_id: str,
        latency_ms: float,
        cost_usd: float = 0.0,
        *,
        request_id: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
    ) -> None:
        stats = self.get(provider_id)
        stats.success_count += 1
        stats.update_latency(latency_ms)
        stats.total_cost_usd += cost_usd
        stats.last_used = time.time()
        if request_id is not None:
            self._decision_log.append({
                "event": "outcome",
                "request_id": request_id,
                "provider_id": provider_id,
                "actual_latency_ms": round(latency_ms, 2),
                "actual_cost_usd": round(cost_usd, 8),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "timestamp": time.time(),
            })

    def record_failure(self, provider_id: str) -> None:
        stats = self.get(provider_id)
        stats.failure_count += 1
        stats.last_used = time.time()

    def log_decision(
        self,
        *,
        request_id: str,
        cost_weight: float,
        candidates: List[str],
        score_breakdown: Dict[str, Dict[str, float]],
        rank_order: List[str],
    ) -> None:
        """Append a routing decision record to the audit trail."""
        self._decision_log.append({
            "event": "decision",
            "request_id": request_id,
            "cost_weight": cost_weight,
            "candidates": candidates,
            "score_breakdown": score_breakdown,
            "rank_order": rank_order,
            "timestamp": time.time(),
        })

    def get_audit_trail(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Return the most recent decision+outcome records."""
        return list(self._decision_log)[-limit:]

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        return {
            provider_id: {
                "ewma_latency_ms": round(stats.ewma_latency_ms, 1),
                "success_rate": round(stats.success_rate, 3),
                "total_cost_usd": round(stats.total_cost_usd, 6),
                "last_used": stats.last_used,
            }
            for provider_id, stats in self._stats.items()
        }


registry = RoutingRegistry()


class LatencyRouter:
    def rank(
        self,
        candidates: List[str],
        provider_costs: Dict[str, tuple[float, float]],
    ) -> List[str]:
        del provider_costs

        def score(provider_id: str) -> float:
            stats = registry.get(provider_id)
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

        latencies = {pid: registry.get(pid).ewma_latency_ms for pid in candidates}
        costs = {pid: sum(provider_costs.get(pid, (0.0, 0.0))) for pid in candidates}
        max_latency = max(latencies.values()) or 1.0
        max_cost = max(costs.values()) or 1.0

        breakdown: Dict[str, Dict[str, float]] = {}

        def score(provider_id: str) -> float:
            stats = registry.get(provider_id)
            normalized_latency = latencies[provider_id] / max_latency
            normalized_cost = costs[provider_id] / max_cost if max_cost else 0.0
            reliability = max(stats.success_rate, 0.1)
            final = (
                (1 - self.cost_weight) * normalized_latency
                + self.cost_weight * normalized_cost
            ) / reliability
            breakdown[provider_id] = {
                "normalized_latency": round(normalized_latency, 4),
                "normalized_cost": round(normalized_cost, 4),
                "reliability": round(reliability, 4),
                "final_score": round(final, 6),
            }
            return final

        ranked = sorted(candidates, key=score)

        # Structured audit log
        logger.info(
            "routing_decision",
            request_id=req_id,
            cost_weight=self.cost_weight,
            candidates=candidates,
            rank_order=ranked,
            score_breakdown=breakdown,
        )
        registry.log_decision(
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
        "best": ["openai", "anthropic", "vertex_ai", "azure_openai"],
        "local": ["ollama_gcp", "llamacpp_gcp", "ollama_local", "aliyun"],
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
            "vertex_ai": "gemini-2.5-flash",
            "azure_openai": "gpt-4o",
        },
        "local": {
            "ollama_gcp": "qwen2.5:3b",
            "llamacpp_gcp": "",
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


def _dispatcher():
    from ..providers.dispatcher import dispatcher

    return dispatcher


def _provider_costs(provider_ids: List[str]) -> Dict[str, tuple[float, float]]:
    dispatch = _dispatcher()
    costs: Dict[str, tuple[float, float]] = {}
    for provider_id in provider_ids:
        provider = dispatch.get_provider(provider_id)
        costs[provider_id] = (provider.COST_INPUT_PER_1K, provider.COST_OUTPUT_PER_1K)
    return costs


def top_providers_for(
    capability: str,
    prefer_local: bool = False,
    prefer_cost: bool = False,
    limit: int = 6,
) -> List[str]:
    dispatch = _dispatcher()
    candidates = dispatch.top_providers_for(
        capability,
        prefer_local=prefer_local,
        prefer_cost=prefer_cost,
        limit=max(1, limit),
    )
    if not candidates:
        return []

    if prefer_cost:
        ranked = cost_router.rank(candidates, _provider_costs(candidates))
        return ranked[: max(1, limit)]

    if prefer_local:
        local_candidates = [provider_id for provider_id in tier_router.providers_for_tier("local") if provider_id in candidates]
        return local_candidates[: max(1, limit)]

    return candidates[: max(1, limit)]


async def route_task(
    task_type: str,
    payload: Dict[str, Any],
    prefer_local: bool = False,
    prefer_cost: bool = False,
    max_retries: int = 2,
    stream: bool = False,
) -> Dict[str, Any]:
    dispatch = _dispatcher()
    candidates = top_providers_for(
        capability=task_type,
        prefer_local=prefer_local,
        prefer_cost=prefer_cost,
        limit=max(1, max_retries + 1),
    )
    if not candidates:
        return {"ok": False, "error": "no providers available", "providers_tried": []}

    last_error = "Routing failed"
    for provider_id in candidates:
        result = await dispatch.invoke_provider(
            provider_id=provider_id,
            model=payload.get("model") if isinstance(payload.get("model"), str) else None,
            payload=payload,
            timeout_ms=int(payload.get("timeout_ms", 30000)),
            stream=stream,
        )
        if isinstance(result, dict) and result.get("ok"):
            result.setdefault("selected_provider", provider_id)
            return result
        if isinstance(result, dict):
            last_error = str(result.get("error", last_error))

    return {
        "ok": False,
        "error": last_error,
        "providers_tried": candidates,
    }


def route_task_sync(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    try:
        asyncio.get_running_loop()
        return {
            "ok": False,
            "error": "route_task_sync cannot run inside an active event loop",
        }
    except RuntimeError:
        return asyncio.run(route_task(*args, **kwargs))
