"""
Feature-based contextual routing model.

Combines deterministic feature scoring (success rate, latency, cost, complexity)
with Thompson Sampling exploration from the existing bandit. Weights are learned
online from routing outcomes and persisted to Supabase routing_weights.

Data flow:
    rank(candidates, costs, task_type, request) → sorted provider list
    record_outcome_by_request_id(request_id, ...)  → gradient weight update
    restore_weights()                              → reload from Supabase at startup

Weight update uses a simple online gradient (perceptron-style) with an adaptive
learning rate that decreases as observation_count grows, so early estimates shift
quickly and later estimates are more stable.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .feature_extractor import ProviderFeatures, RoutingFeatures, feature_extractor

logger = logging.getLogger(__name__)

_MAX_PENDING = 10_000  # cap on un-attributed request feature cache


# ---------------------------------------------------------------------------
# Weight dataclass
# ---------------------------------------------------------------------------


@dataclass
class FeatureWeights:
    task_type: str
    w_success_rate: float = 0.40  # prior: historical quality signal is strongest
    w_latency: float = 0.30  # prior: latency matters a lot for UX
    w_cost: float = 0.20  # prior: cost is secondary to quality/speed
    w_complexity: float = 0.10  # prior: complexity-match bonus
    observation_count: int = 0
    last_updated_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Weights cache
# ---------------------------------------------------------------------------


class WeightsCache:
    """In-memory store of learned FeatureWeights per task_type."""

    def __init__(self) -> None:
        self._weights: Dict[str, FeatureWeights] = {}

    def get(self, task_type: str) -> FeatureWeights:
        if task_type not in self._weights:
            self._weights[task_type] = FeatureWeights(task_type=task_type)
        return self._weights[task_type]

    def update_from_outcome(
        self,
        task_type: str,
        request: RoutingFeatures,
        provider: ProviderFeatures,
        success: bool,
        rating: Optional[int] = None,
    ) -> FeatureWeights:
        w = self.get(task_type)

        # Adaptive learning rate: starts high, decreases as data accumulates
        lr = max(0.05, 0.5 / (1.0 + w.observation_count * 0.01))

        predicted = _compute_base_score(request, provider, w)
        actual = 1.0 if success else 0.0
        if rating is not None:
            actual += 0.25 * rating  # ±0.25 for thumbs up/down
        actual = max(0.0, min(1.25, actual))

        error = actual - predicted

        w.w_success_rate += lr * error * provider.success_rate
        w.w_latency += lr * error * (1.0 - provider.norm_latency)
        w.w_cost += lr * error * (1.0 - provider.norm_cost)
        w.w_complexity += lr * error * provider.success_rate * request.complexity_score

        # Clip then renormalise so weights stay interpretable and sum to 1
        raw = [
            max(0.01, min(1.0, w.w_success_rate)),
            max(0.01, min(1.0, w.w_latency)),
            max(0.01, min(1.0, w.w_cost)),
            max(0.01, min(1.0, w.w_complexity)),
        ]
        total = sum(raw)
        w.w_success_rate = round(raw[0] / total, 6)
        w.w_latency = round(raw[1] / total, 6)
        w.w_cost = round(raw[2] / total, 6)
        w.w_complexity = round(raw[3] / total, 6)

        w.observation_count += 1
        w.last_updated_at = time.time()

        return w

    def to_dict(self, task_type: str) -> dict:
        w = self.get(task_type)
        return {
            "w_success_rate": w.w_success_rate,
            "w_latency": w.w_latency,
            "w_cost": w.w_cost,
            "w_complexity": w.w_complexity,
        }

    def load_from_dict(self, task_type: str, data: dict, observation_count: int = 0) -> None:
        w = self.get(task_type)
        w.w_success_rate = float(data.get("w_success_rate", 0.40))
        w.w_latency = float(data.get("w_latency", 0.30))
        w.w_cost = float(data.get("w_cost", 0.20))
        w.w_complexity = float(data.get("w_complexity", 0.10))
        w.observation_count = observation_count


# ---------------------------------------------------------------------------
# Scoring helper
# ---------------------------------------------------------------------------


def _compute_base_score(
    request: RoutingFeatures,
    provider: ProviderFeatures,
    weights: FeatureWeights,
) -> float:
    if not provider.is_healthy:
        return 0.0
    return (
        weights.w_success_rate * provider.success_rate
        + weights.w_latency * (1.0 - provider.norm_latency)
        + weights.w_cost * (1.0 - provider.norm_cost)
        + weights.w_complexity * provider.success_rate * request.complexity_score
    )


# ---------------------------------------------------------------------------
# Feature router
# ---------------------------------------------------------------------------


class FeatureRouter:
    """
    Contextual feature-based provider ranker with online weight learning.

    For each routing decision, scores all candidates with a linear combination
    of feature signals, blended with Thompson Sampling exploration noise.
    Weights are updated online after each outcome via a gradient nudge.
    """

    def __init__(self, cache: WeightsCache) -> None:
        self._cache = cache
        # request_id → RoutingFeatures captured at rank() time; popped at outcome time
        self._pending: Dict[str, RoutingFeatures] = {}

    def score_provider(
        self,
        request: RoutingFeatures,
        provider: ProviderFeatures,
        weights: FeatureWeights,
        bandit_alpha: float = 1.0,
        bandit_beta: float = 1.0,
    ) -> float:
        if not provider.is_healthy:
            return 0.0

        base = _compute_base_score(request, provider, weights)

        # Blend exploration in inverse proportion to how much data we have.
        # At 0 observations: pure exploration. At 50+: ≤85% deterministic.
        exploitation_ratio = min(weights.observation_count / 50.0, 0.85)
        try:
            noise = random.betavariate(max(bandit_alpha, 0.01), max(bandit_beta, 0.01)) - 0.5
        except Exception:
            noise = 0.0

        return exploitation_ratio * base + (1.0 - exploitation_ratio) * (0.5 + noise)

    def rank(
        self,
        candidates: List[str],
        provider_costs: Dict[str, Tuple[float, float]],
        *,
        task_type: str,
        request: RoutingFeatures,
        request_id: Optional[str] = None,
    ) -> List[str]:
        if not candidates:
            return candidates

        try:
            from api.routing.router_registry import registry  # noqa: PLC0415

            snapshot = registry.snapshot()
        except Exception:
            snapshot = {}

        provider_features = feature_extractor.extract_providers(
            candidates, provider_costs, snapshot
        )
        weights = self._cache.get(task_type)

        bandit_states: Dict[str, Tuple[float, float]] = {}
        try:
            from api.routing.ml_router import bandit_cache  # noqa: PLC0415

            for pid in candidates:
                state = bandit_cache.get(task_type, pid)
                bandit_states[pid] = (state.alpha, state.beta)
        except Exception:
            pass

        scored: List[Tuple[str, float]] = []
        for pid in candidates:
            pf = provider_features.get(pid)
            if pf is None:
                scored.append((pid, 0.5))
                continue
            alpha, beta = bandit_states.get(pid, (1.0, 1.0))
            score = self.score_provider(request, pf, weights, alpha, beta)
            scored.append((pid, score))

        ranked = [p for p, _ in sorted(scored, key=lambda x: x[1], reverse=True)]

        if request_id and len(self._pending) < _MAX_PENDING:
            self._pending[request_id] = request

        return ranked

    def record_outcome(
        self,
        *,
        task_type: str,
        request: RoutingFeatures,
        provider_id: str,
        provider_features: ProviderFeatures,
        success: bool,
        rating: Optional[int] = None,
    ) -> None:
        updated = self._cache.update_from_outcome(
            task_type, request, provider_features, success, rating
        )
        _fire_weights_upsert(
            task_type,
            self._cache.to_dict(task_type),
            updated.observation_count,
        )

    def record_outcome_by_request_id(
        self,
        *,
        request_id: str,
        task_type: str,
        provider_id: str,
        success: bool,
        rating: Optional[int] = None,
    ) -> bool:
        """
        Record an outcome using RoutingFeatures cached at rank() time.
        Returns True if the request_id was found in the pending cache.
        """
        request_features = self._pending.pop(request_id, None)
        if request_features is None:
            return False

        # Re-derive provider features from current registry state (no costs available here)
        snapshot: Dict = {}
        try:
            from api.routing.router_registry import registry  # noqa: PLC0415

            snapshot = registry.snapshot()
        except Exception:
            pass

        pf_map = feature_extractor.extract_providers(
            [provider_id], {provider_id: (0.0, 0.0)}, snapshot
        )
        provider_features = pf_map.get(
            provider_id,
            ProviderFeatures(
                provider_id=provider_id,
                success_rate=0.5,
                norm_latency=0.5,
                norm_cost=0.5,
                is_healthy=True,
            ),
        )

        self.record_outcome(
            task_type=task_type,
            request=request_features,
            provider_id=provider_id,
            provider_features=provider_features,
            success=success,
            rating=rating,
        )
        return True

    async def restore_weights(self) -> None:
        try:
            from api.providers.supabase_events import (  # noqa: PLC0415
                _ENABLED,
                _HEADERS,
                _REST,
                _get_client,
            )

            if not _ENABLED:
                return

            resp = await _get_client().get(
                f"{_REST}/routing_weights",
                headers={**_HEADERS, "Accept": "application/json"},
                params={"select": "task_type,weights,observation_count"},
            )
            rows = resp.json() if resp.status_code == 200 else []
            if not isinstance(rows, list):
                return

            for row in rows:
                try:
                    task_type = row["task_type"]
                    weights_data = row.get("weights") or {}
                    obs_count = int(row.get("observation_count", 0))
                    self._cache.load_from_dict(task_type, weights_data, obs_count)
                except (KeyError, ValueError, TypeError):
                    continue

            logger.info("feature_weights_restored task_types=%d", len(self._cache._weights))
        except Exception as exc:
            logger.warning("feature_weights_restore_failed error=%s", exc)


# ---------------------------------------------------------------------------
# Supabase persistence
# ---------------------------------------------------------------------------


def _fire_weights_upsert(task_type: str, weights: dict, observation_count: int) -> None:
    try:
        from api.providers.supabase_events import (  # noqa: PLC0415
            _HEADERS,
            _REST,
            _fire,
            _get_client,
        )

        async def _upsert() -> None:
            if not _REST:
                return
            try:
                await _get_client().post(
                    f"{_REST}/routing_weights",
                    headers={
                        **_HEADERS,
                        "Prefer": "resolution=merge-duplicates,return=minimal",
                    },
                    json={
                        "task_type": task_type,
                        "weights": weights,
                        "observation_count": observation_count,
                        "last_updated_at": "now()",
                    },
                )
            except Exception as exc:
                logger.debug("weights_upsert_failed error=%s", exc)

        _fire(_upsert())
    except Exception as exc:
        logger.debug("weights_upsert_schedule_failed error=%s", exc)


# ---------------------------------------------------------------------------
# Module singletons
# ---------------------------------------------------------------------------

feature_weights_cache = WeightsCache()
feature_router = FeatureRouter(cache=feature_weights_cache)
