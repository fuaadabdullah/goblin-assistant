"""Forward-only routing pipeline for contextual provider selection.

The public pipeline is intentionally stage-shaped:

Prompt -> Feature Extraction -> Classification -> Policy -> Scoring -> Selection -> Execution

Each stage is a small, injectable boundary. The returned trace makes the flow
observable and gives benchmarks stable per-stage timing points without scraping
logs.
"""

from __future__ import annotations

import importlib
import logging
import time
from dataclasses import dataclass, field, replace
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

_MAX_PENDING = 10_000

logger = logging.getLogger(__name__)

STAGE_PROMPT = "prompt"
STAGE_FEATURE_EXTRACTION = "feature_extraction"
STAGE_CLASSIFICATION = "classification"
STAGE_POLICY = "policy"
STAGE_SCORING = "scoring"
STAGE_SELECTION = "selection"
STAGE_EXECUTION = "execution"
ROUTING_STAGE_ORDER = (
    STAGE_PROMPT,
    STAGE_FEATURE_EXTRACTION,
    STAGE_CLASSIFICATION,
    STAGE_POLICY,
    STAGE_SCORING,
    STAGE_SELECTION,
    STAGE_EXECUTION,
)


@dataclass(frozen=True)
class RoutingPipelineStageTrace:
    """Timing and metadata emitted for one routing stage."""

    name: str
    duration_ms: float
    attributes: Dict[str, Any] = field(default_factory=dict)


RoutingPipelineObserver = Callable[[RoutingPipelineStageTrace], None]


@dataclass(frozen=True)
class RoutingPrompt:
    """Prompt-stage input captured before feature extraction."""

    prompt: str
    conversation_turns: int
    source: str = "prompt"


@dataclass(frozen=True)
class RoutingClassification:
    """Stable task labels produced by the classification stage."""

    task_type: str
    intent_label: str
    intent_confidence: float


@dataclass(frozen=True)
class RoutingExecutionPlan:
    """The selected provider plan handed to downstream execution code."""

    routing_id: str
    task_type: str
    selected_provider_id: Optional[str]
    ranked_provider_ids: List[str]


@dataclass(frozen=True)
class RoutingPipelineScore:
    provider_id: str
    score: float
    pct: int


@dataclass(frozen=True)
class RoutingPipelineResult:
    routing_id: str
    task_type: str
    features: Any
    policy_decision: Any
    scores: List[RoutingPipelineScore]
    classification: Optional[RoutingClassification] = None
    execution_plan: Optional[RoutingExecutionPlan] = None
    trace: List[RoutingPipelineStageTrace] = field(default_factory=list)

    @property
    def selected_provider_id(self) -> Optional[str]:
        if self.execution_plan is None:
            return None
        return self.execution_plan.selected_provider_id


class RoutingPipeline:
    """Runs the router modernization stages in a fixed, observable order."""

    def __init__(
        self,
        *,
        feature_router: Any,
        bandit_cache: Any,
        feature_extractor_service: Any,
        classifier_service: Any,
        policy_engine_service: Any,
        registry: Any = None,
        health_provider_service: Any = None,
        observers: Optional[Sequence[RoutingPipelineObserver]] = None,
    ) -> None:
        self._feature_router = feature_router
        self._bandit_cache = bandit_cache
        self._registry = registry
        self._feature_extractor = feature_extractor_service
        self._classifier = classifier_service
        self._policy_engine = policy_engine_service
        self._health_provider = health_provider_service
        self._observers = list(observers or [])

    def route_prompt(
        self,
        candidates: List[str],
        prompt: str,
        *,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        task_type: Optional[str] = None,
        intent_label: str = "unknown",
        intent_confidence: float = 0.0,
        provider_costs: Optional[Dict[str, Tuple[float, float]]] = None,
        routing_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        prefer_supplied_task_type: bool = False,
    ) -> RoutingPipelineResult:
        """Run the full prompt-to-execution-plan pipeline from raw prompt text."""
        trace: List[RoutingPipelineStageTrace] = []
        history = conversation_history or []

        routing_prompt = self._run_stage(
            STAGE_PROMPT,
            trace,
            lambda: RoutingPrompt(
                prompt=prompt,
                conversation_turns=len(history),
            ),
            lambda result: {
                "source": result.source,
                "prompt_length": len(result.prompt),
                "conversation_turns": result.conversation_turns,
            },
        )
        features = self._run_stage(
            STAGE_FEATURE_EXTRACTION,
            trace,
            lambda: self._feature_extractor.extract_request(
                routing_prompt.prompt,
                task_type or "unknown",
                history,
                intent_label,
                intent_confidence,
            ),
            lambda result: {
                "task_type": getattr(result, "task_type", "unknown"),
                "complexity_score": getattr(result, "complexity_score", 0.0),
            },
        )
        classification = self._run_stage(
            STAGE_CLASSIFICATION,
            trace,
            lambda: self._classify(
                routing_prompt.prompt,
                features,
                fallback_task_type=task_type or "chat",
                prefer_fallback_task_type=prefer_supplied_task_type,
            ),
            lambda result: {
                "task_type": result.task_type,
                "intent_label": result.intent_label,
                "intent_confidence": result.intent_confidence,
            },
        )
        classified_features = replace(
            features,
            task_type=classification.task_type,
            intent_label=classification.intent_label,
            intent_confidence=classification.intent_confidence,
        )
        return self._score_features(
            candidates,
            classified_features,
            task_type=classification.task_type,
            provider_costs=provider_costs,
            routing_id=routing_id,
            metadata=metadata,
            trace=trace,
            classification=classification,
        )

    def score(
        self,
        candidates: List[str],
        features: Any,
        *,
        task_type: str,
        provider_costs: Optional[Dict[str, Tuple[float, float]]] = None,
        routing_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RoutingPipelineResult:
        trace: List[RoutingPipelineStageTrace] = []
        self._run_stage(
            STAGE_PROMPT,
            trace,
            lambda: RoutingPrompt(
                prompt="",
                conversation_turns=int(getattr(features, "conversation_turn", 0) or 0),
                source="precomputed_features",
            ),
            lambda result: {
                "source": result.source,
                "conversation_turns": result.conversation_turns,
            },
        )
        self._run_stage(
            STAGE_FEATURE_EXTRACTION,
            trace,
            lambda: features,
            lambda result: {
                "source": "precomputed_features",
                "task_type": getattr(result, "task_type", task_type),
                "complexity_score": getattr(result, "complexity_score", 0.0),
            },
        )
        classification = self._run_stage(
            STAGE_CLASSIFICATION,
            trace,
            lambda: self._classify("", features, fallback_task_type=task_type),
            lambda result: {
                "task_type": result.task_type,
                "intent_label": result.intent_label,
                "intent_confidence": result.intent_confidence,
            },
        )
        return self._score_features(
            candidates,
            features,
            task_type=classification.task_type,
            provider_costs=provider_costs,
            routing_id=routing_id,
            metadata=metadata,
            trace=trace,
            classification=classification,
        )

    def _score_features(
        self,
        candidates: List[str],
        features: Any,
        *,
        task_type: str,
        provider_costs: Optional[Dict[str, Tuple[float, float]]] = None,
        routing_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        trace: Optional[List[RoutingPipelineStageTrace]] = None,
        classification: Optional[RoutingClassification] = None,
    ) -> RoutingPipelineResult:
        trace = trace if trace is not None else []
        costs: Dict[str, Tuple[float, float]] = provider_costs or {
            provider_id: (0.0, 0.0) for provider_id in candidates
        }

        decision = self._run_stage(
            STAGE_POLICY,
            trace,
            lambda: self._policy_engine.evaluate(features, candidates, metadata=metadata or {}),
            lambda result: {
                "candidate_count": len(candidates),
                "matched_rules": list(getattr(result, "matched_rules", [])),
                "restricted": bool(getattr(result, "restrict_to", None)),
            },
        )
        scored_candidates = decision.apply_restriction(candidates)

        raw_scores = self._run_stage(
            STAGE_SCORING,
            trace,
            lambda: self._score_candidates(
                scored_candidates,
                features,
                task_type=task_type,
                provider_costs=costs,
            ),
            lambda result: {
                "candidate_count": len(scored_candidates),
                "scored_count": len(result),
            },
        )
        decision.apply_boosts(raw_scores)
        percentages = _softmax_pct(raw_scores, temperature=4.0)

        scores = self._run_stage(
            STAGE_SELECTION,
            trace,
            lambda: _select_scores(scored_candidates, raw_scores, percentages),
            lambda result: {
                "selected_provider_id": result[0].provider_id if result else None,
                "ranked_provider_ids": [item.provider_id for item in result],
            },
        )
        execution_plan = self._run_stage(
            STAGE_EXECUTION,
            trace,
            lambda: RoutingExecutionPlan(
                routing_id=routing_id,
                task_type=task_type,
                selected_provider_id=scores[0].provider_id if scores else None,
                ranked_provider_ids=[score.provider_id for score in scores],
            ),
            lambda result: {
                "selected_provider_id": result.selected_provider_id,
                "ranked_provider_ids": result.ranked_provider_ids,
            },
        )

        self.remember_request_features(routing_id, features)
        return RoutingPipelineResult(
            routing_id=routing_id,
            task_type=task_type,
            features=features,
            policy_decision=decision,
            scores=scores,
            classification=classification,
            execution_plan=execution_plan,
            trace=list(trace),
        )

    def _score_candidates(
        self,
        candidates: List[str],
        features: Any,
        *,
        task_type: str,
        provider_costs: Dict[str, Tuple[float, float]],
    ) -> Dict[str, float]:
        snapshot = self._registry.snapshot() if self._registry is not None else {}
        health_availability = self._provider_health_availability(candidates)
        provider_features_map = self._feature_extractor.extract_providers(
            candidates,
            provider_costs,
            snapshot,
            health_availability=health_availability,
        )
        weights = self._feature_router._cache.get(task_type)

        raw_scores: Dict[str, float] = {}
        for provider_id in candidates:
            provider_features = provider_features_map.get(
                provider_id,
                SimpleNamespace(
                    provider_id=provider_id,
                    success_rate=0.5,
                    norm_latency=0.5,
                    norm_cost=0.5,
                    is_healthy=True,
                ),
            )
            bandit_state = self._bandit_cache.get(task_type, provider_id)
            raw_scores[provider_id] = self._feature_router.score_provider(
                features,
                provider_features,
                weights,
                bandit_alpha=bandit_state.alpha,
                bandit_beta=bandit_state.beta,
            )
        return raw_scores

    def _classify(
        self,
        prompt: str,
        features: Any,
        *,
        fallback_task_type: str = "chat",
        prefer_fallback_task_type: bool = False,
    ) -> RoutingClassification:
        task_type = fallback_task_type
        if prompt and prefer_fallback_task_type and fallback_task_type != "unknown":
            task_type = fallback_task_type
        elif prompt:
            classify = getattr(self._classifier, "classify", None)
            if callable(classify):
                task_type = str(classify(prompt) or task_type)
        else:
            task_type = str(getattr(features, "task_type", None) or fallback_task_type)

        intent_label = str(getattr(features, "intent_label", None) or task_type)
        if intent_label == "unknown":
            intent_label = task_type
        intent_confidence = float(getattr(features, "intent_confidence", 0.0) or 0.0)
        if prompt and intent_confidence <= 0.0:
            intent_confidence = 0.5

        return RoutingClassification(
            task_type=task_type,
            intent_label=intent_label,
            intent_confidence=round(max(0.0, min(1.0, intent_confidence)), 4),
        )

    def rank(
        self,
        candidates: List[str],
        provider_costs: Dict[str, Tuple[float, float]],
        *,
        task_type: str,
        request: Any,
        request_id: Optional[str] = None,
    ) -> List[str]:
        if "_cache" not in getattr(self._feature_router, "__dict__", {}):
            rank = getattr(self._feature_router, "rank", None)
            if callable(rank):
                return rank(
                    candidates,
                    provider_costs,
                    task_type=task_type,
                    request=request,
                    request_id=request_id,
                )

        routing_id = request_id or ""
        result = self.score(
            candidates,
            request,
            task_type=task_type,
            provider_costs=provider_costs,
            routing_id=routing_id,
        )
        return [score.provider_id for score in result.scores]

    def remember_request_features(self, routing_id: str, features: Any) -> None:
        if not routing_id:
            return
        pending = getattr(self._feature_router, "_pending", None)
        if isinstance(pending, dict) and len(pending) < _MAX_PENDING:
            pending[routing_id] = features
            return
        remember = getattr(self._feature_router, "remember_request_features", None)
        if callable(remember):
            remember(routing_id, features)

    def record_outcome_by_request_id(
        self,
        *,
        request_id: str,
        task_type: str,
        provider_id: str,
        success: bool,
        rating: Optional[int] = None,
    ) -> bool:
        return self._feature_router.record_outcome_by_request_id(
            request_id=request_id,
            task_type=task_type,
            provider_id=provider_id,
            success=success,
            rating=rating,
        )

    def _provider_health_availability(self, provider_ids: List[str]) -> Optional[Dict[str, bool]]:
        if self._health_provider is None:
            return None
        try:
            return dict(self._health_provider.availability_for(provider_ids))
        except Exception:
            return None

    def _run_stage(
        self,
        name: str,
        trace: List[RoutingPipelineStageTrace],
        action: Callable[[], Any],
        attributes: Optional[Callable[[Any], Dict[str, Any]]] = None,
    ) -> Any:
        start = time.perf_counter()
        try:
            result = action()
        except Exception as exc:
            self._record_stage(
                trace,
                name,
                start,
                {"error": exc.__class__.__name__},
            )
            raise

        attrs: Dict[str, Any] = {}
        if attributes is not None:
            try:
                attrs = attributes(result)
            except Exception as exc:
                attrs = {"attribute_error": exc.__class__.__name__}
        self._record_stage(trace, name, start, attrs)
        return result

    def _record_stage(
        self,
        trace: List[RoutingPipelineStageTrace],
        name: str,
        start: float,
        attributes: Dict[str, Any],
    ) -> None:
        record = RoutingPipelineStageTrace(
            name=name,
            duration_ms=round((time.perf_counter() - start) * 1000.0, 4),
            attributes=attributes,
        )
        trace.append(record)
        logger.debug(
            "routing_pipeline_stage_completed",
            extra={
                "stage": record.name,
                "duration_ms": record.duration_ms,
                "attributes": record.attributes,
            },
        )
        for observer in list(self._observers):
            try:
                observer(record)
            except Exception as exc:
                logger.debug("routing_pipeline_observer_failed error=%s", exc)


def build_routing_pipeline(
    *,
    bandit_cache: Any,
    feature_router: Any = None,
    feature_extractor_service: Any = None,
    classifier_service: Any = None,
    policy_engine_service: Any = None,
    registry: Any = None,
    health_provider_service: Any = None,
    observers: Optional[Sequence[RoutingPipelineObserver]] = None,
) -> RoutingPipeline:
    if feature_router is None:
        feature_router = importlib.import_module("api.routing.feature_router").feature_router
    if feature_extractor_service is None:
        feature_extractor_service = importlib.import_module(
            "api.routing.feature_extractor"
        ).feature_extractor
    if classifier_service is None:
        classifier_service = importlib.import_module(
            "api.routing.prompt_classifier"
        ).prompt_classifier
    if policy_engine_service is None:
        policy_engine_service = importlib.import_module("api.routing.policy_rules").policy_engine
    if health_provider_service is None:
        health_provider_service = importlib.import_module(
            "api.routing.health_provider"
        ).health_provider

    return RoutingPipeline(
        feature_router=feature_router,
        bandit_cache=bandit_cache,
        feature_extractor_service=feature_extractor_service,
        classifier_service=classifier_service,
        policy_engine_service=policy_engine_service,
        registry=registry,
        health_provider_service=health_provider_service,
        observers=observers,
    )


def _select_scores(
    candidates: List[str],
    raw_scores: Dict[str, float],
    percentages: Dict[str, int],
) -> List[RoutingPipelineScore]:
    scores = [
        RoutingPipelineScore(provider_id=pid, score=raw_scores[pid], pct=percentages[pid])
        for pid in candidates
    ]
    scores.sort(key=lambda item: item.score, reverse=True)
    return scores


def _softmax_pct(scores: Dict[str, float], temperature: float = 1.0) -> Dict[str, int]:
    import math

    if not scores:
        return {}

    scaled = {provider_id: score / temperature for provider_id, score in scores.items()}
    max_value = max(scaled.values())
    exp_values = {provider_id: math.exp(value - max_value) for provider_id, value in scaled.items()}
    total = sum(exp_values.values()) or 1.0
    return {provider_id: round(value / total * 100) for provider_id, value in exp_values.items()}
