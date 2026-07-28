"""Tests for policy-engine wiring and explainability in routing/provider_selection.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from api.routing.policy_rules import PolicyDecision
from api.routing.provider_selection import ProviderSelectionModel, get_explanation
from api.routing.routing_pipeline import ROUTING_STAGE_ORDER


def _mock_routing_features(**overrides):
    defaults = dict(
        prompt_length_bucket=1,
        task_type="chat",
        complexity_score=0.5,
        conversation_turn=0,
        intent_label="chat",
        intent_confidence=0.8,
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def _mock_ml_modules():
    bandit_state = MagicMock(alpha=1.0, beta=1.0)
    bandit_cache = MagicMock()
    bandit_cache.get.return_value = bandit_state

    feature_router = MagicMock()
    feature_router._cache.get.return_value = MagicMock()
    feature_router._pending = {}
    feature_router.score_provider.return_value = 0.5

    registry = MagicMock()
    registry.snapshot.return_value = {}

    return {
        "api.routing.feature_router": MagicMock(feature_router=feature_router),
        "api.routing.ml_router": MagicMock(bandit_cache=bandit_cache),
        "api.routing.router_registry": MagicMock(registry=registry),
    }


class TestPolicyIntegration:
    def test_policy_boost_shifts_ranking(self):
        model = ProviderSelectionModel()
        boosted_decision = PolicyDecision(boosts={"anthropic": 1.0}, matched_rules=["coding_boost"])

        with patch.dict("sys.modules", _mock_ml_modules()):
            with patch("api.routing.provider_selection.feature_extractor") as mock_fe:
                mock_fe.extract_providers.return_value = {}
                with patch(
                    "api.routing.provider_selection.policy_engine.evaluate",
                    return_value=boosted_decision,
                ):
                    result = model.score(
                        ["openai", "anthropic"],
                        _mock_routing_features(),
                        task_type="coding",
                    )

        assert result[0].provider_id == "anthropic"

    def test_policy_restriction_filters_candidates(self):
        model = ProviderSelectionModel()
        restricted_decision = PolicyDecision(
            restrict_to={"ollama_local"}, matched_rules=["confidential"]
        )

        with patch.dict("sys.modules", _mock_ml_modules()):
            with patch("api.routing.provider_selection.feature_extractor") as mock_fe:
                mock_fe.extract_providers.return_value = {}
                with patch(
                    "api.routing.provider_selection.policy_engine.evaluate",
                    return_value=restricted_decision,
                ):
                    result = model.score(
                        ["openai", "ollama_local"],
                        _mock_routing_features(),
                        task_type="chat",
                    )

        assert {r.provider_id for r in result} == {"ollama_local"}

    def test_metadata_passed_through_to_policy_engine(self):
        model = ProviderSelectionModel()

        with patch.dict("sys.modules", _mock_ml_modules()):
            with patch("api.routing.provider_selection.feature_extractor") as mock_fe:
                mock_fe.extract_providers.return_value = {}
                with patch(
                    "api.routing.provider_selection.policy_engine.evaluate",
                    return_value=PolicyDecision(),
                ) as mock_evaluate:
                    model.score(
                        ["openai"],
                        _mock_routing_features(),
                        task_type="chat",
                        metadata={"confidential": True},
                    )

        _, kwargs = mock_evaluate.call_args
        assert kwargs["metadata"] == {"confidential": True}


class TestExplainability:
    def test_explanation_stored_and_retrievable(self):
        model = ProviderSelectionModel()

        with patch.dict("sys.modules", _mock_ml_modules()):
            with patch("api.routing.provider_selection.feature_extractor") as mock_fe:
                mock_fe.extract_providers.return_value = {}
                model.score(
                    ["openai", "anthropic"],
                    _mock_routing_features(intent_label="coding"),
                    task_type="coding",
                    routing_id="explain-test-1",
                )

        explanation = get_explanation("explain-test-1")
        assert explanation is not None
        assert explanation["routing_id"] == "explain-test-1"
        assert explanation["task_type"] == "coding"
        assert explanation["intent"] == "coding"
        assert explanation["chosen_provider"] in {"openai", "anthropic"}
        assert len(explanation["candidates"]) == 2

    def test_unknown_routing_id_returns_none(self):
        assert get_explanation("never-existed") is None

    def test_matched_policies_recorded_in_explanation(self):
        model = ProviderSelectionModel()
        decision = PolicyDecision(boosts={"anthropic": 0.1}, matched_rules=["coding_boost"])

        with patch.dict("sys.modules", _mock_ml_modules()):
            with patch("api.routing.provider_selection.feature_extractor") as mock_fe:
                mock_fe.extract_providers.return_value = {}
                with patch(
                    "api.routing.provider_selection.policy_engine.evaluate",
                    return_value=decision,
                ):
                    model.score(
                        ["openai", "anthropic"],
                        _mock_routing_features(),
                        task_type="coding",
                        routing_id="explain-test-2",
                    )

        explanation = get_explanation("explain-test-2")
        assert explanation["matched_policies"] == ["coding_boost"]
        assert explanation["policy_boosts"] == {"anthropic": 0.1}

    def test_stage_trace_recorded_in_explanation(self):
        model = ProviderSelectionModel()

        with patch.dict("sys.modules", _mock_ml_modules()):
            with patch("api.routing.provider_selection.feature_extractor") as mock_fe:
                mock_fe.extract_providers.return_value = {}
                model.score(
                    ["openai", "anthropic"],
                    _mock_routing_features(),
                    task_type="chat",
                    routing_id="explain-stage-trace",
                )

        explanation = get_explanation("explain-stage-trace")
        assert explanation is not None
        assert [entry["stage"] for entry in explanation["routing_trace"]] == list(
            ROUTING_STAGE_ORDER
        )
        assert all(entry["duration_ms"] >= 0 for entry in explanation["routing_trace"])
