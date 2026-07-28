"""Extended tests for routing/ml_router.py — BanditState, BanditCache, BanditRouter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from api.routing.ml_router import (
    BanditCache,
    BanditRouter,
    BanditState,
    _sample_beta,
    bandit_cache,
    bandit_router,
)

# ── BanditState dataclass ─────────────────────────────────────────────────────


class TestBanditState:
    def test_defaults(self):
        s = BanditState(task_type="chat", provider_id="openai")
        assert s.alpha == pytest.approx(1.0)
        assert s.beta == pytest.approx(1.0)
        assert s.observation_count == 0

    def test_explicit_construction(self):
        s = BanditState(
            task_type="code", provider_id="anthropic", alpha=3.0, beta=2.0, observation_count=5
        )
        assert s.alpha == pytest.approx(3.0)
        assert s.observation_count == 5


# ── BanditCache ───────────────────────────────────────────────────────────────


class TestBanditCacheGet:
    def test_cold_start_returns_prior(self):
        cache = BanditCache()
        state = cache.get("chat", "openai")
        assert state.alpha == pytest.approx(1.0)
        assert state.beta == pytest.approx(1.0)
        assert state.observation_count == 0

    def test_same_key_returns_same_object(self):
        cache = BanditCache()
        s1 = cache.get("chat", "openai")
        s2 = cache.get("chat", "openai")
        assert s1 is s2

    def test_different_task_types_are_independent(self):
        cache = BanditCache()
        cache.get("chat", "openai").alpha = 5.0
        state_code = cache.get("code", "openai")
        assert state_code.alpha == pytest.approx(1.0)

    def test_different_providers_are_independent(self):
        cache = BanditCache()
        cache.get("chat", "openai").alpha = 8.0
        state_anthropic = cache.get("chat", "anthropic")
        assert state_anthropic.alpha == pytest.approx(1.0)


class TestBanditCacheUpdate:
    def test_success_true_increments_alpha(self):
        cache = BanditCache()
        state = cache.update("chat", "openai", success=True)
        assert state.alpha == pytest.approx(2.0)
        assert state.beta == pytest.approx(1.0)
        assert state.observation_count == 1

    def test_success_false_increments_beta(self):
        cache = BanditCache()
        state = cache.update("chat", "openai", success=False)
        assert state.alpha == pytest.approx(1.0)
        assert state.beta == pytest.approx(2.0)
        assert state.observation_count == 1

    def test_success_none_no_observation_count_change(self):
        cache = BanditCache()
        state = cache.update("chat", "openai", success=None)
        assert state.observation_count == 0

    def test_rating_plus_one_nudges_alpha(self):
        cache = BanditCache()
        state = cache.update("chat", "openai", success=None, rating=1)
        assert state.alpha == pytest.approx(1.5)
        assert state.beta == pytest.approx(1.0)

    def test_rating_minus_one_nudges_beta(self):
        cache = BanditCache()
        state = cache.update("chat", "openai", success=None, rating=-1)
        assert state.alpha == pytest.approx(1.0)
        assert state.beta == pytest.approx(1.5)

    def test_success_true_with_rating_plus_one_stacks(self):
        cache = BanditCache()
        state = cache.update("chat", "openai", success=True, rating=1)
        assert state.alpha == pytest.approx(2.5)  # 1 + 1.0 (success) + 0.5 (rating)
        assert state.observation_count == 1

    def test_success_false_with_rating_minus_one_stacks(self):
        cache = BanditCache()
        state = cache.update("chat", "openai", success=False, rating=-1)
        assert state.beta == pytest.approx(2.5)
        assert state.observation_count == 1

    def test_multiple_updates_accumulate(self):
        cache = BanditCache()
        cache.update("chat", "openai", success=True)
        cache.update("chat", "openai", success=True)
        cache.update("chat", "openai", success=False)
        state = cache.get("chat", "openai")
        assert state.alpha == pytest.approx(3.0)
        assert state.beta == pytest.approx(2.0)
        assert state.observation_count == 3

    def test_returns_updated_state(self):
        cache = BanditCache()
        state = cache.update("chat", "openai", success=True)
        assert isinstance(state, BanditState)


class TestBanditCacheHasSufficientData:
    def test_no_observations_returns_false(self):
        cache = BanditCache()
        assert cache.has_sufficient_data("chat", "openai", min_obs=3) is False

    def test_missing_key_returns_false(self):
        cache = BanditCache()
        assert cache.has_sufficient_data("chat", "missing", min_obs=1) is False

    def test_enough_observations_returns_true(self):
        cache = BanditCache()
        for _ in range(3):
            cache.update("chat", "openai", success=True)
        assert cache.has_sufficient_data("chat", "openai", min_obs=3) is True

    def test_exactly_at_minimum_returns_true(self):
        cache = BanditCache()
        cache.update("chat", "openai", success=True)
        assert cache.has_sufficient_data("chat", "openai", min_obs=1) is True


class TestBanditCacheMarkLoaded:
    def test_not_loaded_by_default(self):
        cache = BanditCache()
        assert cache.is_loaded is False

    def test_mark_loaded_sets_flag(self):
        cache = BanditCache()
        cache.mark_loaded()
        assert cache.is_loaded is True


# ── _sample_beta ──────────────────────────────────────────────────────────────


class TestSampleBeta:
    def test_returns_float(self):
        state = BanditState(task_type="chat", provider_id="openai")
        result = _sample_beta(state)
        assert isinstance(result, float)

    def test_result_in_unit_interval(self):
        state = BanditState(task_type="chat", provider_id="openai")
        for _ in range(20):
            assert 0.0 <= _sample_beta(state) <= 1.0

    def test_heavily_positive_prior_skews_high(self):
        state = BanditState(task_type="chat", provider_id="openai", alpha=100.0, beta=1.0)
        samples = [_sample_beta(state) for _ in range(50)]
        assert sum(samples) / len(samples) > 0.8

    def test_heavily_negative_prior_skews_low(self):
        state = BanditState(task_type="chat", provider_id="openai", alpha=1.0, beta=100.0)
        samples = [_sample_beta(state) for _ in range(50)]
        assert sum(samples) / len(samples) < 0.2


# ── BanditRouter.rank ─────────────────────────────────────────────────────────


class TestBanditRouterRank:
    def _make_router(self):
        cache = BanditCache()
        fallback = MagicMock()
        fallback.rank.return_value = []
        return BanditRouter(cache=cache, fallback=fallback, min_observations=2), cache

    def test_empty_candidates_returns_empty(self):
        router, _ = self._make_router()
        result = router.rank([], {}, task_type="chat")
        assert result == []

    def test_all_cold_start_uses_fallback(self):
        router, _ = self._make_router()
        router._fallback.rank.return_value = ["openai", "anthropic"]
        result = router.rank(["openai", "anthropic"], {}, task_type="chat")
        assert set(result) == {"openai", "anthropic"}
        router._fallback.rank.assert_called_once()

    def test_with_sufficient_bandit_data_skips_fallback(self):
        router, cache = self._make_router()
        # Give openai enough data to be in the bandit set
        cache.update("chat", "openai", success=True)
        cache.update("chat", "openai", success=True)
        # Fallback should pass through anthropic (cold-start provider)
        router._fallback.rank.return_value = ["anthropic"]
        result = router.rank(["openai", "anthropic"], {}, task_type="chat")
        assert "openai" in result
        assert "anthropic" in result

    def test_feature_router_path_used_when_request_provided(self):
        router, _ = self._make_router()
        mock_request = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "api.routing.feature_router": MagicMock(
                    feature_router=MagicMock(rank=MagicMock(return_value=["anthropic", "openai"]))
                ),
            },
        ):
            result = router.rank(
                ["openai", "anthropic"], {}, task_type="chat", request=mock_request
            )

        assert result == ["anthropic", "openai"]

    def test_feature_router_failure_falls_back_to_thompson(self):
        router, _ = self._make_router()
        mock_request = MagicMock()
        router._fallback.rank.return_value = ["openai", "anthropic"]

        with patch.dict(
            "sys.modules",
            {
                "api.routing.feature_router": MagicMock(
                    feature_router=MagicMock(
                        rank=MagicMock(side_effect=RuntimeError("feature down"))
                    )
                ),
            },
        ):
            result = router.rank(
                ["openai", "anthropic"], {}, task_type="chat", request=mock_request
            )

        assert set(result) == {"openai", "anthropic"}

    def test_all_results_preserved_no_duplication(self):
        router, _ = self._make_router()
        router._fallback.rank.return_value = ["a", "b", "c"]
        result = router.rank(["a", "b", "c"], {}, task_type="chat")
        assert sorted(result) == ["a", "b", "c"]


# ── BanditRouter.record_outcome ───────────────────────────────────────────────


class TestBanditRouterRecordOutcome:
    def test_updates_bandit_cache(self):
        cache = BanditCache()
        fallback = MagicMock()
        router = BanditRouter(cache=cache, fallback=fallback)

        with patch.dict(
            "sys.modules",
            {
                "api.providers.supabase_events": MagicMock(_fire=MagicMock(), _post=MagicMock()),
            },
        ):
            router.record_outcome(
                request_id="req-1",
                task_type="chat",
                provider_id="openai",
                was_selected=True,
                latency_ms=100.0,
                cost_usd=0.001,
                success=True,
            )

        state = cache.get("chat", "openai")
        assert state.observation_count == 1
        assert state.alpha > 1.0


# ── Singleton ─────────────────────────────────────────────────────────────────


def test_bandit_cache_singleton_exists():
    assert bandit_cache is not None
    assert isinstance(bandit_cache, BanditCache)


def test_bandit_router_singleton_exists():
    assert bandit_router is not None
    assert isinstance(bandit_router, BanditRouter)
