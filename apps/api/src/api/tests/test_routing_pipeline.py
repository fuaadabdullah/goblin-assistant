from __future__ import annotations

from types import SimpleNamespace

from api.routing.feature_extractor import ProviderFeatures, RoutingFeatures
from api.routing.policy_rules import PolicyDecision
from api.routing.routing_pipeline import (
    ROUTING_STAGE_ORDER,
    RoutingPipeline,
    RoutingPipelineStageTrace,
)


class FakeFeatureExtractor:
    def extract_request(
        self,
        prompt: str,
        task_type: str,
        conversation_history: list[dict],
        intent_label: str = "unknown",
        intent_confidence: float = 0.0,
    ) -> RoutingFeatures:
        return RoutingFeatures(
            prompt_length_bucket=0,
            task_type=task_type,
            complexity_score=0.7 if "refactor" in prompt.lower() else 0.2,
            conversation_turn=len(conversation_history),
            intent_label=intent_label,
            intent_confidence=intent_confidence,
        )

    def extract_providers(
        self,
        candidates,
        provider_costs,
        registry_snapshot,
        health_availability=None,
    ):
        health_availability = health_availability or {}
        return {
            provider_id: ProviderFeatures(
                provider_id=provider_id,
                success_rate=0.9 if provider_id == "anthropic" else 0.5,
                norm_latency=0.2 if provider_id == "anthropic" else 0.6,
                norm_cost=0.4,
                is_healthy=health_availability.get(provider_id, True),
            )
            for provider_id in candidates
        }


class FakeClassifier:
    def classify(self, prompt: str) -> str:
        return "code" if "refactor" in prompt.lower() else "chat"


class CapturingPolicyEngine:
    def __init__(self) -> None:
        self.seen_task_type = None

    def evaluate(self, features, candidates, *, metadata=None) -> PolicyDecision:
        self.seen_task_type = features.task_type
        return PolicyDecision(boosts={"openai": 0.2}, matched_rules=["prefer_openai"])


class FakeFeatureRouter:
    def __init__(self) -> None:
        self._cache = SimpleNamespace(get=lambda _task_type: SimpleNamespace())
        self._pending = {}

    def score_provider(
        self,
        request,
        provider,
        weights,
        *,
        bandit_alpha: float,
        bandit_beta: float,
    ) -> float:
        return provider.success_rate

    def record_outcome_by_request_id(self, **_kwargs) -> bool:
        return True


class FakeBanditCache:
    def get(self, task_type: str, provider_id: str):
        return SimpleNamespace(alpha=1.0, beta=1.0)


class FakeRegistry:
    def snapshot(self):
        return {}


class FakeHealthProvider:
    def availability_for(self, provider_ids):
        return {provider_id: True for provider_id in provider_ids}


def _pipeline(*, observer=None, policy_engine=None) -> RoutingPipeline:
    observers = [observer] if observer is not None else []
    return RoutingPipeline(
        feature_router=FakeFeatureRouter(),
        bandit_cache=FakeBanditCache(),
        feature_extractor_service=FakeFeatureExtractor(),
        classifier_service=FakeClassifier(),
        policy_engine_service=policy_engine or CapturingPolicyEngine(),
        registry=FakeRegistry(),
        health_provider_service=FakeHealthProvider(),
        observers=observers,
    )


def test_route_prompt_runs_named_stages_in_order_and_emits_observer_records():
    observed: list[RoutingPipelineStageTrace] = []
    pipeline = _pipeline(observer=observed.append)

    result = pipeline.route_prompt(
        ["openai", "anthropic"],
        "Please refactor this routing code",
        routing_id="route-1",
    )

    assert [stage.name for stage in result.trace] == list(ROUTING_STAGE_ORDER)
    assert [stage.name for stage in observed] == list(ROUTING_STAGE_ORDER)
    assert all(stage.duration_ms >= 0 for stage in result.trace)
    assert result.classification is not None
    assert result.classification.task_type == "code"
    assert result.execution_plan is not None
    assert result.selected_provider_id == "anthropic"
    assert result.execution_plan.ranked_provider_ids == ["anthropic", "openai"]


def test_classification_stage_updates_features_before_policy():
    policy_engine = CapturingPolicyEngine()
    pipeline = _pipeline(policy_engine=policy_engine)

    result = pipeline.route_prompt(
        ["openai"],
        "Please refactor this class",
        routing_id="route-2",
    )

    assert policy_engine.seen_task_type == "code"
    assert result.features.task_type == "code"
    assert result.trace[2].attributes["task_type"] == "code"


def test_route_prompt_can_preserve_supplied_task_type_for_live_pipeline():
    policy_engine = CapturingPolicyEngine()
    pipeline = _pipeline(policy_engine=policy_engine)

    result = pipeline.route_prompt(
        ["openai"],
        "Please refactor this class",
        task_type="coding",
        intent_label="coding",
        intent_confidence=0.9,
        routing_id="route-preserve-task",
        prefer_supplied_task_type=True,
    )

    assert policy_engine.seen_task_type == "coding"
    assert result.features.task_type == "coding"
    assert result.classification is not None
    assert result.classification.task_type == "coding"


def test_score_with_precomputed_features_keeps_full_stage_trace():
    pipeline = _pipeline()
    features = RoutingFeatures(
        prompt_length_bucket=1,
        task_type="chat",
        complexity_score=0.4,
        conversation_turn=3,
        intent_label="chat",
        intent_confidence=0.8,
    )

    result = pipeline.score(
        ["openai", "anthropic"],
        features,
        task_type="chat",
        routing_id="route-3",
    )

    assert [stage.name for stage in result.trace] == list(ROUTING_STAGE_ORDER)
    assert result.trace[0].attributes["source"] == "precomputed_features"
    assert result.classification is not None
    assert result.classification.intent_label == "chat"
