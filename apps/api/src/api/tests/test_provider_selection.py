"""Tests for routing/provider_selection.py — _softmax_pct and ProviderSelectionModel."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from api.routing.provider_selection import (
    ProviderScore,
    ProviderSelectionModel,
    _softmax_pct,
    provider_selection_model,
)

# ── ProviderScore dataclass ───────────────────────────────────────────────────


class TestProviderScore:
    def test_construction(self):
        ps = ProviderScore(provider_id="openai", score=0.8, pct=80)
        assert ps.provider_id == "openai"
        assert ps.score == pytest.approx(0.8)
        assert ps.pct == 80

    def test_model_name_defaults_to_empty_string(self):
        ps = ProviderScore(provider_id="anthropic", score=0.7, pct=70)
        assert ps.model_name == ""

    def test_model_name_set(self):
        ps = ProviderScore(
            provider_id="anthropic", score=0.9, pct=90, model_name="claude-sonnet-4-6"
        )
        assert ps.model_name == "claude-sonnet-4-6"


# ── _softmax_pct ──────────────────────────────────────────────────────────────


class TestSoftmaxPct:
    def test_empty_dict_returns_empty(self):
        assert _softmax_pct({}) == {}

    def test_single_provider_gets_100(self):
        result = _softmax_pct({"openai": 0.8})
        assert result["openai"] == 100

    def test_two_equal_scores_near_50_each(self):
        result = _softmax_pct({"openai": 0.5, "anthropic": 0.5})
        assert result["openai"] == pytest.approx(50, abs=2)
        assert result["anthropic"] == pytest.approx(50, abs=2)

    def test_percentages_sum_to_100(self):
        scores = {"openai": 0.8, "anthropic": 0.7, "gemini": 0.6}
        result = _softmax_pct(scores)
        assert sum(result.values()) == pytest.approx(100, abs=2)

    def test_higher_score_gets_higher_pct(self):
        result = _softmax_pct({"strong": 0.9, "weak": 0.1})
        assert result["strong"] > result["weak"]

    def test_temperature_spreads_scores(self):
        scores = {"a": 0.6, "b": 0.4}
        low_temp = _softmax_pct(scores, temperature=0.1)
        high_temp = _softmax_pct(scores, temperature=10.0)
        # Low temperature → winner takes more; high temperature → closer to equal
        diff_low = abs(low_temp["a"] - low_temp["b"])
        diff_high = abs(high_temp["a"] - high_temp["b"])
        assert diff_low > diff_high

    def test_three_providers_all_get_percentage(self):
        scores = {"a": 0.9, "b": 0.5, "c": 0.3}
        result = _softmax_pct(scores)
        assert all(result[k] > 0 for k in scores)

    def test_all_zero_scores_equal_percentages(self):
        scores = {"a": 0.0, "b": 0.0, "c": 0.0}
        result = _softmax_pct(scores)
        assert result["a"] == result["b"] == result["c"]


# ── ProviderSelectionModel.score ──────────────────────────────────────────────


def _mock_routing_features():
    return MagicMock(
        prompt_length_bucket=1,
        task_type="chat",
        complexity_score=0.5,
        conversation_turn=0,
        intent_label="chat",
        intent_confidence=0.8,
    )


def _mock_ml_modules(scores_override=None):
    """Build sys.modules mock for feature_router, ml_router, router_registry."""
    bandit_state = MagicMock()
    bandit_state.alpha = 1.0
    bandit_state.beta = 1.0

    bandit_cache = MagicMock()
    bandit_cache.get.return_value = bandit_state

    weights = MagicMock()

    feature_router = MagicMock()
    feature_router._cache.get.return_value = weights
    feature_router._pending = {}
    feature_router.score_provider.return_value = 0.7

    registry = MagicMock()
    registry.snapshot.return_value = {}

    return {
        "api.routing.feature_router": MagicMock(feature_router=feature_router),
        "api.routing.ml_router": MagicMock(bandit_cache=bandit_cache),
        "api.routing.router_registry": MagicMock(registry=registry),
    }


class TestProviderSelectionModelScore:
    def test_empty_candidates_returns_empty(self):
        model = ProviderSelectionModel()
        result = model.score([], _mock_routing_features(), task_type="chat")
        assert result == []

    def test_returns_list_of_provider_scores(self):
        model = ProviderSelectionModel()
        with patch.dict("sys.modules", _mock_ml_modules()):
            with patch("api.routing.provider_selection.feature_extractor") as mock_fe:
                mock_fe.extract_providers.return_value = {}
                result = model.score(
                    ["openai", "anthropic"], _mock_routing_features(), task_type="chat"
                )

        assert isinstance(result, list)
        assert all(isinstance(r, ProviderScore) for r in result)

    def test_all_candidates_represented(self):
        model = ProviderSelectionModel()
        candidates = ["openai", "anthropic", "gemini"]
        with patch.dict("sys.modules", _mock_ml_modules()):
            with patch("api.routing.provider_selection.feature_extractor") as mock_fe:
                mock_fe.extract_providers.return_value = {}
                result = model.score(candidates, _mock_routing_features(), task_type="chat")

        result_ids = {r.provider_id for r in result}
        assert result_ids == set(candidates)

    def test_model_error_falls_back_to_equal_scores(self):
        model = ProviderSelectionModel()
        # sys.modules with None makes imports fail
        with patch.dict(
            "sys.modules",
            {
                "api.routing.feature_router": None,
                "api.routing.ml_router": None,
                "api.routing.router_registry": None,
            },
        ):
            result = model.score(
                ["openai", "anthropic"], _mock_routing_features(), task_type="chat"
            )

        assert len(result) == 2
        assert all(r.score == pytest.approx(0.5) for r in result)
        assert all(r.pct == 50 for r in result)

    def test_sorted_by_score_descending(self):
        model = ProviderSelectionModel()
        call_count = [0]

        def score_side_effect(
            request_features, provider_features, weights, *, bandit_alpha, bandit_beta
        ):
            call_count[0] += 1
            return 0.9 if call_count[0] == 1 else 0.3

        with patch.dict("sys.modules", _mock_ml_modules()):
            with patch("api.routing.provider_selection.feature_extractor") as mock_fe:
                mock_fe.extract_providers.return_value = {}
                mods = _mock_ml_modules()
                mods[
                    "api.routing.feature_router"
                ].feature_router.score_provider.side_effect = score_side_effect
                with patch.dict("sys.modules", mods):
                    result = model.score(
                        ["first", "second"], _mock_routing_features(), task_type="chat"
                    )

        scores = [r.score for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_pct_sum_near_100(self):
        model = ProviderSelectionModel()
        with patch.dict("sys.modules", _mock_ml_modules()):
            with patch("api.routing.provider_selection.feature_extractor") as mock_fe:
                mock_fe.extract_providers.return_value = {}
                result = model.score(["a", "b", "c"], _mock_routing_features(), task_type="chat")

        total_pct = sum(r.pct for r in result)
        assert total_pct == pytest.approx(100, abs=5)

    def test_routing_id_stored_in_pending(self):
        model = ProviderSelectionModel()
        pending = {}

        mods = _mock_ml_modules()
        mods["api.routing.feature_router"].feature_router._pending = pending

        with patch.dict("sys.modules", mods):
            with patch("api.routing.provider_selection.feature_extractor") as mock_fe:
                mock_fe.extract_providers.return_value = {}
                model.score(
                    ["openai"], _mock_routing_features(), task_type="chat", routing_id="test-id-123"
                )

        assert "test-id-123" in pending

    def test_custom_routing_id_used(self):
        model = ProviderSelectionModel()
        with patch.dict("sys.modules", _mock_ml_modules()):
            with patch("api.routing.provider_selection.feature_extractor") as mock_fe:
                mock_fe.extract_providers.return_value = {}
                result = model.score(
                    ["openai"], _mock_routing_features(), task_type="chat", routing_id="custom-id"
                )
        assert len(result) == 1

    def test_singleton_instance_exists(self):
        assert provider_selection_model is not None
        assert isinstance(provider_selection_model, ProviderSelectionModel)
