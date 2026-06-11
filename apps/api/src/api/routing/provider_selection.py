"""Provider Selection Model — Goblin's brain for choosing which LLM to call.

Given a request's feature vector and a list of candidate providers, scores each
candidate using the combined feature+bandit model and returns a ranked list with
explicit percentage scores:

    score([openai, anthropic, gemini], features, task_type="coding")
    → [ProviderScore("anthropic", 0.82, 82),
       ProviderScore("openai",    0.74, 74),
       ProviderScore("gemini",    0.51, 51)]

Scoring combines:
  - Learned feature weights (success_rate, latency, cost, complexity) from FeatureRouter
  - Thompson Sampling exploration noise from BanditCache
  - Exploitation ratio that shifts from exploration → exploitation as data accumulates

The model also stores request features in the feature router's pending cache so
outcomes can be recorded later via record_outcome_by_request_id().
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import structlog

from .feature_extractor import ProviderFeatures, RoutingFeatures, feature_extractor

logger = structlog.get_logger()


@dataclass
class ProviderScore:
    """Scored candidate from ProviderSelectionModel."""

    provider_id: str
    score: float  # raw combined score [0, 1]
    pct: int  # display percentage (0–100), softmax-normalised
    model_name: str = ""  # model paired with this provider in the department chain


class ProviderSelectionModel:
    """Scores all candidate providers and returns a ranked list with percentages.

    This is the single place where feature weights + bandit priors combine
    into a routing decision. Every call is attributable (via routing_id) so
    outcomes can be fed back to improve future selections.
    """

    def score(
        self,
        candidates: List[str],
        features: RoutingFeatures,
        *,
        task_type: str,
        provider_costs: Optional[Dict[str, Tuple[float, float]]] = None,
        routing_id: Optional[str] = None,
    ) -> List[ProviderScore]:
        """Score each candidate and return a ranked list with percentages.

        Args:
            candidates: Provider IDs to score (e.g. ["openai", "anthropic", "gemini"]).
            features: RoutingFeatures extracted from the current request.
            task_type: Task-type key for weight and bandit lookups (e.g. "coding").
            provider_costs: Optional (input_cost, output_cost) per provider for
                            cost normalisation. Zeros are safe — omits cost signal.
            routing_id: Correlation ID used to attribute outcomes back to this
                        decision. Auto-generated if not provided.

        Returns:
            Providers sorted best-first with scores and display percentages.
        """
        if not candidates:
            return []

        routing_id = routing_id or str(uuid.uuid4())
        costs: Dict[str, Tuple[float, float]] = provider_costs or {
            p: (0.0, 0.0) for p in candidates
        }

        try:
            return self._score_with_model(candidates, features, task_type, costs, routing_id)
        except Exception as exc:
            logger.warning("provider_selection_model_failed", task_type=task_type, error=str(exc))
            # Fallback: equal scores, preserve original order
            return [ProviderScore(pid, 0.5, 50) for pid in candidates]

    def _score_with_model(
        self,
        candidates: List[str],
        features: RoutingFeatures,
        task_type: str,
        costs: Dict[str, Tuple[float, float]],
        routing_id: str,
    ) -> List[ProviderScore]:
        from api.routing.feature_router import feature_router  # noqa: PLC0415
        from api.routing.ml_router import bandit_cache  # noqa: PLC0415
        from api.routing.router_registry import registry  # noqa: PLC0415

        snapshot = registry.snapshot()
        provider_features_map = feature_extractor.extract_providers(candidates, costs, snapshot)
        weights = feature_router._cache.get(task_type)

        raw_scores: Dict[str, float] = {}
        for pid in candidates:
            pf = provider_features_map.get(
                pid,
                ProviderFeatures(
                    provider_id=pid,
                    success_rate=0.5,
                    norm_latency=0.5,
                    norm_cost=0.5,
                    is_healthy=True,
                ),
            )
            bandit_state = bandit_cache.get(task_type, pid)
            score = feature_router.score_provider(
                features,
                pf,
                weights,
                bandit_alpha=bandit_state.alpha,
                bandit_beta=bandit_state.beta,
            )
            raw_scores[pid] = score

        # Softmax-normalise so percentages reflect relative confidence, not
        # absolute score magnitude. Temperature=4 keeps the output spread wide.
        pcts = _softmax_pct(raw_scores, temperature=4.0)

        results = [
            ProviderScore(provider_id=pid, score=raw_scores[pid], pct=pcts[pid])
            for pid in candidates
        ]
        results.sort(key=lambda x: x.score, reverse=True)

        # Register features in the pending cache so outcomes can be attributed later
        if routing_id and len(feature_router._pending) < 10_000:
            feature_router._pending[routing_id] = features

        logger.debug(
            "provider_selection_scored",
            task_type=task_type,
            routing_id=routing_id,
            scores={r.provider_id: r.pct for r in results},
        )
        return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _softmax_pct(scores: Dict[str, float], temperature: float = 1.0) -> Dict[str, int]:
    """Convert raw scores to display percentages via softmax.

    Uses temperature scaling so closely-ranked providers spread out readably
    rather than converging toward 33%/33%/33%.
    """
    if not scores:
        return {}

    scaled = {pid: s / temperature for pid, s in scores.items()}
    max_val = max(scaled.values())
    # Subtract max for numerical stability
    exp_vals = {pid: math.exp(v - max_val) for pid, v in scaled.items()}
    total = sum(exp_vals.values()) or 1.0
    return {pid: round(e / total * 100) for pid, e in exp_vals.items()}


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

provider_selection_model = ProviderSelectionModel()
