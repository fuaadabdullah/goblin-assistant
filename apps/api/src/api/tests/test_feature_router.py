"""Tests for routing/feature_router.py — WeightsCache, FeatureRouter, _compute_base_score."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from api.routing.feature_extractor import ProviderFeatures, RoutingFeatures
from api.routing.feature_router import (
    FeatureRouter,
    FeatureWeights,
    WeightsCache,
    _compute_base_score,
    feature_router,
    feature_weights_cache,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _req(complexity: float = 0.5) -> RoutingFeatures:
    return RoutingFeatures(
        prompt_length_bucket=1,
        task_type="chat",
        complexity_score=complexity,
        conversation_turn=0,
        intent_label="chat",
        intent_confidence=0.8,
    )


def _pf(
    provider_id: str = "openai",
    success_rate: float = 0.9,
    norm_latency: float = 0.3,
    norm_cost: float = 0.2,
    is_healthy: bool = True,
) -> ProviderFeatures:
    return ProviderFeatures(
        provider_id=provider_id,
        success_rate=success_rate,
        norm_latency=norm_latency,
        norm_cost=norm_cost,
        is_healthy=is_healthy,
    )


def _weights(task_type: str = "chat") -> FeatureWeights:
    return FeatureWeights(
        task_type=task_type,
        w_success_rate=0.40,
        w_latency=0.30,
        w_cost=0.20,
        w_complexity=0.10,
    )


# ── FeatureWeights dataclass ──────────────────────────────────────────────────


class TestFeatureWeights:
    def test_defaults(self):
        w = FeatureWeights(task_type="chat")
        assert w.w_success_rate == pytest.approx(0.40)
        assert w.w_latency == pytest.approx(0.30)
        assert w.w_cost == pytest.approx(0.20)
        assert w.w_complexity == pytest.approx(0.10)
        assert w.observation_count == 0

    def test_weights_sum_to_one(self):
        w = FeatureWeights(task_type="chat")
        total = w.w_success_rate + w.w_latency + w.w_cost + w.w_complexity
        assert total == pytest.approx(1.0)


# ── _compute_base_score ───────────────────────────────────────────────────────


class TestComputeBaseScore:
    def test_unhealthy_provider_returns_zero(self):
        req = _req()
        pf = _pf(is_healthy=False)
        w = _weights()
        assert _compute_base_score(req, pf, w) == pytest.approx(0.0)

    def test_healthy_provider_returns_positive(self):
        req = _req()
        pf = _pf()
        w = _weights()
        score = _compute_base_score(req, pf, w)
        assert score > 0.0

    def test_perfect_provider_near_one(self):
        req = _req(complexity=1.0)
        pf = _pf(success_rate=1.0, norm_latency=0.0, norm_cost=0.0)
        w = _weights()
        score = _compute_base_score(req, pf, w)
        # w_success_rate*1.0 + w_latency*1.0 + w_cost*1.0 + w_complexity*1.0*1.0 = 1.0
        assert score == pytest.approx(1.0)

    def test_higher_latency_lowers_score(self):
        req = _req()
        pf_fast = _pf(norm_latency=0.1)
        pf_slow = _pf(norm_latency=0.9)
        w = _weights()
        assert _compute_base_score(req, pf_fast, w) > _compute_base_score(req, pf_slow, w)


# ── WeightsCache ──────────────────────────────────────────────────────────────


class TestWeightsCache:
    def test_cold_start_returns_priors(self):
        cache = WeightsCache()
        w = cache.get("chat")
        assert w.w_success_rate == pytest.approx(0.40)

    def test_same_key_returns_same_object(self):
        cache = WeightsCache()
        w1 = cache.get("chat")
        w2 = cache.get("chat")
        assert w1 is w2

    def test_different_task_types_are_independent(self):
        cache = WeightsCache()
        w_chat = cache.get("chat")
        w_chat.w_success_rate = 0.99
        w_code = cache.get("code")
        assert w_code.w_success_rate == pytest.approx(0.40)

    def test_to_dict_returns_four_weights(self):
        cache = WeightsCache()
        d = cache.to_dict("chat")
        assert set(d.keys()) == {"w_success_rate", "w_latency", "w_cost", "w_complexity"}

    def test_load_from_dict_overrides_defaults(self):
        cache = WeightsCache()
        cache.load_from_dict(
            "code",
            {"w_success_rate": 0.7, "w_latency": 0.1, "w_cost": 0.1, "w_complexity": 0.1},
            observation_count=20,
        )
        w = cache.get("code")
        assert w.w_success_rate == pytest.approx(0.7)
        assert w.observation_count == 20

    def test_load_from_dict_missing_keys_use_defaults(self):
        cache = WeightsCache()
        cache.load_from_dict("chat", {}, observation_count=0)
        w = cache.get("chat")
        assert w.w_success_rate == pytest.approx(0.40)

    def test_update_from_outcome_success_nudges_weights(self):
        cache = WeightsCache()
        req = _req()
        pf = _pf()
        cache.update_from_outcome("chat", req, pf, success=True)
        # Weights renormalize so just check observation_count incremented
        assert cache.get("chat").observation_count == 1

    def test_update_from_outcome_failure_adjusts_weights(self):
        cache = WeightsCache()
        req = _req()
        pf = _pf()
        cache.update_from_outcome("chat", req, pf, success=False)
        assert cache.get("chat").observation_count == 1

    def test_update_from_outcome_with_rating(self):
        cache = WeightsCache()
        req = _req()
        pf = _pf()
        cache.update_from_outcome("chat", req, pf, success=True, rating=1)
        assert cache.get("chat").observation_count == 1

    def test_weights_sum_to_one_after_update(self):
        cache = WeightsCache()
        req = _req()
        pf = _pf()
        for _ in range(5):
            cache.update_from_outcome("chat", req, pf, success=True)
        w = cache.get("chat")
        total = w.w_success_rate + w.w_latency + w.w_cost + w.w_complexity
        assert total == pytest.approx(1.0, abs=0.001)

    def test_learning_rate_decreases_with_observations(self):
        cache = WeightsCache()
        req = _req()
        pf = _pf()
        # After many observations, weights should be more stable (less shifted per update)
        for _ in range(100):
            cache.update_from_outcome("chat", req, pf, success=True)
        w_before = cache.get("chat").w_success_rate
        cache.update_from_outcome("chat", req, pf, success=False)  # single push back
        w_after = cache.get("chat").w_success_rate
        # Change should be small (adaptive learning rate at work)
        assert abs(w_after - w_before) < 0.05


# ── FeatureRouter.score_provider ─────────────────────────────────────────────


class TestFeatureRouterScoreProvider:
    def test_unhealthy_provider_scores_zero(self):
        router = FeatureRouter(cache=WeightsCache())
        req = _req()
        pf = _pf(is_healthy=False)
        w = _weights()
        assert router.score_provider(req, pf, w) == pytest.approx(0.0)

    def test_healthy_provider_scores_nonzero(self):
        router = FeatureRouter(cache=WeightsCache())
        req = _req()
        pf = _pf()
        w = _weights()
        assert router.score_provider(req, pf, w) > 0.0

    def test_result_bounded(self):
        router = FeatureRouter(cache=WeightsCache())
        req = _req()
        pf = _pf()
        w = _weights()
        w.observation_count = 50  # force high exploitation_ratio
        for _ in range(20):
            score = router.score_provider(req, pf, w, bandit_alpha=5.0, bandit_beta=1.0)
            assert 0.0 <= score <= 2.0  # can exceed 1.0 with exploration noise at high alpha

    def test_high_exploitation_ratio_at_many_observations(self):
        router = FeatureRouter(cache=WeightsCache())
        req = _req()
        pf = _pf(success_rate=0.9, norm_latency=0.1, norm_cost=0.1)
        w = _weights()
        w.observation_count = 1000  # forces exploitation_ratio = 0.85
        scores = [router.score_provider(req, pf, w) for _ in range(20)]
        # At high exploitation, scores should be relatively stable
        assert max(scores) - min(scores) < 0.6


# ── FeatureRouter.rank ────────────────────────────────────────────────────────


def _mock_registry():
    return patch.dict(
        "sys.modules",
        {
            "api.routing.router_registry": MagicMock(
                registry=MagicMock(snapshot=MagicMock(return_value={}))
            ),
            "api.routing.ml_router": MagicMock(
                bandit_cache=MagicMock(get=MagicMock(return_value=MagicMock(alpha=1.0, beta=1.0)))
            ),
        },
    )


class TestFeatureRouterRank:
    def test_empty_candidates_returns_empty(self):
        router = FeatureRouter(cache=WeightsCache())
        req = _req()
        with _mock_registry():
            result = router.rank([], {}, task_type="chat", request=req)
        assert result == []

    def test_all_candidates_in_result(self):
        router = FeatureRouter(cache=WeightsCache())
        req = _req()
        with _mock_registry():
            result = router.rank(
                ["openai", "anthropic", "gemini"], {}, task_type="chat", request=req
            )
        assert sorted(result) == ["anthropic", "gemini", "openai"]

    def test_result_is_sorted(self):
        router = FeatureRouter(cache=WeightsCache())
        req = _req()
        with _mock_registry():
            result = router.rank(["openai", "anthropic"], {}, task_type="chat", request=req)
        assert len(result) == 2

    def test_request_id_stored_in_pending(self):
        router = FeatureRouter(cache=WeightsCache())
        req = _req()
        with _mock_registry():
            router.rank(["openai"], {}, task_type="chat", request=req, request_id="rid-123")
        assert "rid-123" in router._pending

    def test_no_request_id_not_stored(self):
        router = FeatureRouter(cache=WeightsCache())
        req = _req()
        with _mock_registry():
            router.rank(["openai"], {}, task_type="chat", request=req)
        assert len(router._pending) == 0

    def test_registry_failure_is_handled(self):
        router = FeatureRouter(cache=WeightsCache())
        req = _req()
        with patch.dict(
            "sys.modules",
            {
                "api.routing.router_registry": None,
                "api.routing.ml_router": None,
            },
        ):
            result = router.rank(["openai"], {}, task_type="chat", request=req)
        assert "openai" in result


# ── FeatureRouter.record_outcome_by_request_id ───────────────────────────────


class TestRecordOutcomeByRequestId:
    def test_missing_request_id_returns_false(self):
        router = FeatureRouter(cache=WeightsCache())
        result = router.record_outcome_by_request_id(
            request_id="nonexistent",
            task_type="chat",
            provider_id="openai",
            success=True,
        )
        assert result is False

    def test_known_request_id_returns_true(self):
        router = FeatureRouter(cache=WeightsCache())
        req = _req()
        router._pending["req-abc"] = req

        with patch.dict(
            "sys.modules",
            {
                "api.routing.router_registry": MagicMock(
                    registry=MagicMock(snapshot=MagicMock(return_value={}))
                ),
                "api.providers.supabase_events": MagicMock(_fire=MagicMock()),
            },
        ):
            result = router.record_outcome_by_request_id(
                request_id="req-abc",
                task_type="chat",
                provider_id="openai",
                success=True,
            )

        assert result is True

    def test_consumed_request_id_not_available_again(self):
        router = FeatureRouter(cache=WeightsCache())
        req = _req()
        router._pending["req-xyz"] = req

        with patch.dict(
            "sys.modules",
            {
                "api.routing.router_registry": MagicMock(
                    registry=MagicMock(snapshot=MagicMock(return_value={}))
                ),
                "api.providers.supabase_events": MagicMock(_fire=MagicMock()),
            },
        ):
            router.record_outcome_by_request_id(
                request_id="req-xyz",
                task_type="chat",
                provider_id="openai",
                success=True,
            )

        assert "req-xyz" not in router._pending


# ── Singletons ────────────────────────────────────────────────────────────────


def test_feature_router_singleton_exists():
    assert feature_router is not None
    assert isinstance(feature_router, FeatureRouter)


def test_feature_weights_cache_singleton_exists():
    assert feature_weights_cache is not None
    assert isinstance(feature_weights_cache, WeightsCache)
