"""
Feature extraction for ML-based provider routing.

Produces two dataclasses per routing decision:
- RoutingFeatures: prompt-level signals extracted from the request
- ProviderFeatures: provider-level signals normalised against the candidate set
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class RoutingFeatures:
    """Per-request feature vector extracted from the prompt and conversation context."""

    prompt_length_bucket: int  # 0=short(<400), 1=medium(<1600), 2=long(<6400), 3=very_long
    task_type: str  # from prompt_classifier (e.g. "code", "reasoning", "chat")
    complexity_score: float  # 0–1 heuristic
    conversation_turn: int  # number of prior messages, capped at 10
    intent_label: str = "unknown"  # from IntentClassifier (e.g. "coding", "research")
    intent_confidence: float = 0.0  # 0–1 classification confidence


@dataclass
class ProviderFeatures:
    """Per-provider feature vector normalised against the current candidate set."""

    provider_id: str
    success_rate: float  # 0–1 from EWMA registry
    norm_latency: float  # 0–1, relative to highest-latency candidate
    norm_cost: float  # 0–1, relative to most-expensive candidate
    is_healthy: bool


_COMPLEXITY_KEYWORDS = [
    "explain",
    "analyse",
    "analyze",
    "compare",
    "tradeoff",
    "trade-off",
    "why",
    "how does",
]
_DEPTH_KEYWORDS = [
    "step by step",
    "in detail",
    "comprehensive",
    "thoroughly",
    "exhaustive",
]


class FeatureExtractor:
    def extract_request(
        self,
        prompt: str,
        task_type: str,
        conversation_history: List[Dict],
        intent_label: str = "unknown",
        intent_confidence: float = 0.0,
    ) -> RoutingFeatures:
        char_count = len(prompt)

        if char_count < 400:
            bucket = 0
        elif char_count < 1600:
            bucket = 1
        elif char_count < 6400:
            bucket = 2
        else:
            bucket = 3

        lower = prompt.lower()
        score = 0.0
        score += min(prompt.count("?") / 3.0, 0.3)
        score += min(len(re.findall(r"```", prompt)) / 4.0, 0.2)
        score += 0.15 if any(kw in lower for kw in _COMPLEXITY_KEYWORDS) else 0.0
        score += 0.15 if any(kw in lower for kw in _DEPTH_KEYWORDS) else 0.0
        score += min(char_count / 4000.0, 0.2)
        complexity = min(score, 1.0)

        turn = min(len(conversation_history), 10)

        return RoutingFeatures(
            prompt_length_bucket=bucket,
            task_type=task_type,
            complexity_score=round(complexity, 4),
            conversation_turn=turn,
            intent_label=intent_label,
            intent_confidence=round(intent_confidence, 4),
        )

    def extract_providers(
        self,
        candidates: List[str],
        provider_costs: Dict[str, Tuple[float, float]],
        registry_snapshot: Dict,
    ) -> Dict[str, ProviderFeatures]:
        """Build ProviderFeatures for each candidate, normalised against the set."""
        if not candidates:
            return {}

        raw_latencies: Dict[str, float] = {}
        raw_costs: Dict[str, float] = {}

        for pid in candidates:
            stats = registry_snapshot.get(pid) or {}
            raw_latencies[pid] = float(stats.get("ewma_latency_ms", 5000.0))
            c = provider_costs.get(pid, (0.0, 0.0))
            raw_costs[pid] = float(c[0] + c[1])

        max_latency = max(raw_latencies.values()) or 1.0
        max_cost = max(raw_costs.values()) or 1.0

        health_monitor: Optional[object] = None
        try:
            from api.services.provider_health import health_monitor as _hm  # noqa: PLC0415

            health_monitor = _hm
        except Exception:
            pass

        result: Dict[str, ProviderFeatures] = {}
        for pid in candidates:
            stats = registry_snapshot.get(pid) or {}
            success_rate = float(stats.get("success_rate", 0.5))

            is_healthy = True
            if health_monitor is not None:
                try:
                    is_healthy = health_monitor.is_available(pid)  # type: ignore[union-attr]
                except Exception:
                    pass

            result[pid] = ProviderFeatures(
                provider_id=pid,
                success_rate=max(0.0, min(1.0, success_rate)),
                norm_latency=raw_latencies[pid] / max_latency,
                norm_cost=raw_costs[pid] / max_cost,
                is_healthy=is_healthy,
            )

        return result


feature_extractor = FeatureExtractor()
