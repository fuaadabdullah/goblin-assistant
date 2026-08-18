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

import importlib
import math
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import structlog

from .feature_extractor import RoutingFeatures, feature_extractor
from .policy_rules import policy_engine
from .routing_pipeline import build_routing_pipeline

logger = structlog.get_logger()

_MAX_EXPLANATIONS = 2_000  # bounded cache of routing_id -> explanation dict


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

    def __init__(self) -> None:
        self._pipeline_cache_key: Optional[tuple[int, ...]] = None
        self._pipeline_cache: Any = None

    def score(
        self,
        candidates: List[str],
        features: RoutingFeatures,
        *,
        task_type: str,
        provider_costs: Optional[Dict[str, Tuple[float, float]]] = None,
        routing_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
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
            metadata: Optional request metadata (e.g. {"confidential": True}) that
                      declarative policy rules can match on. See policy_rules.py.

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
            return self._score_with_model(
                candidates, features, task_type, costs, routing_id, metadata or {}
            )
        except Exception as exc:
            logger.warning("provider_selection_model_failed", task_type=task_type, error=str(exc))
            # Fallback: equal scores, preserve original order
            return [ProviderScore(pid, 0.5, 50) for pid in candidates]

    def score_prompt(
        self,
        candidates: List[str],
        prompt: str,
        *,
        task_type: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        intent_label: str = "unknown",
        intent_confidence: float = 0.0,
        provider_costs: Optional[Dict[str, Tuple[float, float]]] = None,
        routing_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        prefer_supplied_task_type: bool = True,
    ) -> List[ProviderScore]:
        """Score candidates from raw prompt text through the staged routing pipeline."""
        if not candidates:
            return []

        routing_id = routing_id or str(uuid.uuid4())
        costs: Dict[str, Tuple[float, float]] = provider_costs or {
            p: (0.0, 0.0) for p in candidates
        }

        try:
            return self._score_prompt_with_model(
                candidates,
                prompt,
                task_type=task_type,
                conversation_history=conversation_history or [],
                intent_label=intent_label,
                intent_confidence=intent_confidence,
                costs=costs,
                routing_id=routing_id,
                metadata=metadata or {},
                prefer_supplied_task_type=prefer_supplied_task_type,
            )
        except Exception as exc:
            logger.warning(
                "provider_selection_prompt_model_failed",
                task_type=task_type,
                error=str(exc),
            )
            return [ProviderScore(pid, 0.5, 50) for pid in candidates]

    def _score_with_model(
        self,
        candidates: List[str],
        features: RoutingFeatures,
        task_type: str,
        costs: Dict[str, Tuple[float, float]],
        routing_id: str,
        metadata: Dict[str, Any],
    ) -> List[ProviderScore]:
        from api.routing.ml_router import bandit_cache
        from api.routing.router_registry import registry

        pipeline_result = self._pipeline_for(
            bandit_cache=bandit_cache,
            registry=registry,
        ).score(
            candidates,
            features,
            task_type=task_type,
            provider_costs=costs,
            routing_id=routing_id,
            metadata=metadata,
        )
        results = [
            ProviderScore(
                provider_id=item.provider_id,
                score=item.score,
                pct=item.pct,
            )
            for item in pipeline_result.scores
        ]

        _store_explanation(
            routing_id,
            task_type=task_type,
            features=features,
            results=results,
            policy_decision=pipeline_result.policy_decision,
            routing_trace=pipeline_result.trace,
        )

        logger.debug(
            "provider_selection_scored",
            task_type=task_type,
            routing_id=routing_id,
            scores={r.provider_id: r.pct for r in results},
            matched_policies=pipeline_result.policy_decision.matched_rules,
        )
        return results

    def _score_prompt_with_model(
        self,
        candidates: List[str],
        prompt: str,
        *,
        task_type: str,
        conversation_history: List[Dict[str, Any]],
        intent_label: str,
        intent_confidence: float,
        costs: Dict[str, Tuple[float, float]],
        routing_id: str,
        metadata: Dict[str, Any],
        prefer_supplied_task_type: bool,
    ) -> List[ProviderScore]:
        from api.routing.ml_router import bandit_cache
        from api.routing.router_registry import registry

        pipeline_result = self._pipeline_for(
            bandit_cache=bandit_cache,
            registry=registry,
        ).route_prompt(
            candidates,
            prompt,
            conversation_history=conversation_history,
            task_type=task_type,
            intent_label=intent_label,
            intent_confidence=intent_confidence,
            provider_costs=costs,
            routing_id=routing_id,
            metadata=metadata,
            prefer_supplied_task_type=prefer_supplied_task_type,
        )
        results = [
            ProviderScore(
                provider_id=item.provider_id,
                score=item.score,
                pct=item.pct,
            )
            for item in pipeline_result.scores
        ]

        _store_explanation(
            routing_id,
            task_type=pipeline_result.task_type,
            features=pipeline_result.features,
            results=results,
            policy_decision=pipeline_result.policy_decision,
            routing_trace=pipeline_result.trace,
        )

        logger.debug(
            "provider_selection_prompt_scored",
            task_type=pipeline_result.task_type,
            routing_id=routing_id,
            scores={r.provider_id: r.pct for r in results},
            matched_policies=pipeline_result.policy_decision.matched_rules,
        )
        return results

    def _pipeline_for(self, *, bandit_cache: Any, registry: Any) -> Any:
        feature_router = importlib.import_module("api.routing.feature_router").feature_router
        classifier = importlib.import_module("api.routing.prompt_classifier").prompt_classifier
        health_provider = importlib.import_module("api.routing.health_provider").health_provider
        cache_key = (
            id(feature_router),
            id(bandit_cache),
            id(feature_extractor),
            id(classifier),
            id(policy_engine),
            id(registry),
            id(health_provider),
        )
        if self._pipeline_cache is not None and self._pipeline_cache_key == cache_key:
            return self._pipeline_cache

        self._pipeline_cache = build_routing_pipeline(
            bandit_cache=bandit_cache,
            feature_router=feature_router,
            feature_extractor_service=feature_extractor,
            classifier_service=classifier,
            policy_engine_service=policy_engine,
            registry=registry,
            health_provider_service=health_provider,
        )
        self._pipeline_cache_key = cache_key
        return self._pipeline_cache


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
# Explainability — "why did Goblin pick this provider?"
# ---------------------------------------------------------------------------

_explanations: Dict[str, Dict[str, Any]] = {}
_explanation_order: List[str] = []  # FIFO eviction order, parallel to _explanations


def _store_explanation(
    routing_id: str,
    *,
    task_type: str,
    features: RoutingFeatures,
    results: List[ProviderScore],
    policy_decision: "object",
    routing_trace: Optional[List[Any]] = None,
) -> None:
    if not routing_id:
        return

    chosen = results[0] if results else None
    trace_entries = [_trace_entry(stage) for stage in routing_trace or []]
    matched_policies = list(getattr(policy_decision, "matched_rules", []))
    candidates = [
        {"provider_id": r.provider_id, "score": round(r.score, 4), "pct": r.pct} for r in results
    ]
    fallback_reasons = _fallback_reasons(chosen, results)
    ml_confidence = _ml_confidence(results)
    prompt_classification = {
        "task_type": task_type,
        "intent": features.intent_label,
        "intent_confidence": features.intent_confidence,
        "complexity_score": features.complexity_score,
        "prompt_length_bucket": features.prompt_length_bucket,
        "retrieval_probability": getattr(features, "retrieval_probability", 0.0),
        "tool_probability": getattr(features, "tool_probability", 0.0),
        "latency_sensitivity": getattr(features, "latency_sensitivity", 0.0),
    }
    _explanations[routing_id] = {
        "routing_id": routing_id,
        "created_at": time.time(),
        "task_type": task_type,
        "intent": features.intent_label,
        "intent_confidence": features.intent_confidence,
        "complexity_score": features.complexity_score,
        "prompt_length_bucket": features.prompt_length_bucket,
        "matched_policies": matched_policies,
        "policy_boosts": dict(getattr(policy_decision, "boosts", {})),
        "candidates": candidates,
        "chosen_provider": chosen.provider_id if chosen else None,
        "chosen_model": chosen.model_name if chosen else None,
        "selection_reason": _selection_reason(chosen, matched_policies, ml_confidence),
        "fallback_reasons": fallback_reasons,
        "prompt_classification": prompt_classification,
        "ml_confidence": ml_confidence,
        "routing_waterfall": trace_entries,
        "routing_trace": trace_entries,
        "latency_percentiles_ms": _stage_latency_percentiles(trace_entries),
    }
    _explanation_order.append(routing_id)
    if len(_explanation_order) > _MAX_EXPLANATIONS:
        stale = _explanation_order.pop(0)
        _explanations.pop(stale, None)


def get_explanation(routing_id: str) -> Optional[Dict[str, Any]]:
    """Return the stored routing explanation for a routing_id, if still cached."""
    return _explanations.get(routing_id)


def get_recent_explanations(limit: int = 200) -> List[Dict[str, Any]]:
    """Return recent routing explanations in newest-first order."""
    clamped = max(1, min(limit, _MAX_EXPLANATIONS))
    recent_ids = list(_explanation_order)[-clamped:]
    return [
        _explanations[routing_id]
        for routing_id in reversed(recent_ids)
        if routing_id in _explanations
    ]


def _trace_entry(stage: Any) -> Dict[str, Any]:
    return {
        "stage": str(getattr(stage, "name", "")),
        "duration_ms": float(getattr(stage, "duration_ms", 0.0)),
        "attributes": dict(getattr(stage, "attributes", {}) or {}),
    }


def _selection_reason(
    chosen: Optional[ProviderScore],
    matched_policies: List[str],
    ml_confidence: Dict[str, Any],
) -> str:
    if chosen is None:
        return "No provider selected after policy and scoring."
    policy_text = f" with policy rules {', '.join(matched_policies)}" if matched_policies else ""
    return (
        f"{chosen.provider_id} ranked first{policy_text}; "
        f"confidence={ml_confidence['selected_confidence']:.2f}, "
        f"margin={ml_confidence['selection_margin']:.2f}."
    )


def _fallback_reasons(
    chosen: Optional[ProviderScore],
    results: List[ProviderScore],
) -> List[Dict[str, Any]]:
    if chosen is None:
        return [
            {
                "provider_id": score.provider_id,
                "reason": "candidate_available_but_no_selection",
                "score": round(score.score, 4),
                "pct": score.pct,
            }
            for score in results
        ]

    reasons: List[Dict[str, Any]] = []
    for score in results[1:]:
        reasons.append(
            {
                "provider_id": score.provider_id,
                "reason": "ranked_below_selected_provider",
                "score": round(score.score, 4),
                "pct": score.pct,
                "score_delta": round(chosen.score - score.score, 4),
                "pct_delta": chosen.pct - score.pct,
            }
        )
    return reasons


def _ml_confidence(results: List[ProviderScore]) -> Dict[str, Any]:
    if not results:
        return {
            "selected_confidence": 0.0,
            "runner_up_confidence": 0.0,
            "selection_margin": 0.0,
            "confidence_source": "provider_score_softmax",
        }
    selected = results[0].pct / 100.0
    runner_up = results[1].pct / 100.0 if len(results) > 1 else 0.0
    return {
        "selected_confidence": round(selected, 4),
        "runner_up_confidence": round(runner_up, 4),
        "selection_margin": round(max(0.0, selected - runner_up), 4),
        "confidence_source": "provider_score_softmax",
    }


def _stage_latency_percentiles(trace_entries: List[Dict[str, Any]]) -> Dict[str, float]:
    samples = sorted(max(0.0, float(entry.get("duration_ms") or 0.0)) for entry in trace_entries)
    if not samples:
        return {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}

    def percentile(value: float) -> float:
        if len(samples) == 1:
            return samples[0]
        rank = (len(samples) - 1) * value
        lower = int(rank)
        upper = min(lower + 1, len(samples) - 1)
        weight = rank - lower
        return samples[lower] * (1.0 - weight) + samples[upper] * weight

    return {
        "p50": round(percentile(0.50), 4),
        "p90": round(percentile(0.90), 4),
        "p95": round(percentile(0.95), 4),
        "p99": round(percentile(0.99), 4),
    }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

provider_selection_model = ProviderSelectionModel()
