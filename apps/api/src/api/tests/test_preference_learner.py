"""Unit tests for PreferenceLearner."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from api.services.preference_learner import (
    PreferenceLearner,
    _bucket_tokens,
    _default_profile,
    _ewma,
    _merge_defaults,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_learner(
    stored_profile: dict | None = None,
) -> tuple[PreferenceLearner, AsyncMock, AsyncMock]:
    """Return a PreferenceLearner with mocked PreferencesService methods."""
    learner = PreferenceLearner()
    get_mock = AsyncMock(return_value=stored_profile or {})
    update_mock = AsyncMock(return_value=None)
    return learner, get_mock, update_mock


# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_bucket_tokens_concise(self):
        assert _bucket_tokens(100) == "concise"
        assert _bucket_tokens(350) == "concise"

    def test_bucket_tokens_medium(self):
        assert _bucket_tokens(351) == "medium"
        assert _bucket_tokens(799) == "medium"

    def test_bucket_tokens_verbose(self):
        assert _bucket_tokens(800) == "verbose"
        assert _bucket_tokens(2000) == "verbose"

    def test_ewma_explicit_positive_raises_affinity(self):
        result = _ewma(0.5, 1.0, 0.20)
        assert result == pytest.approx(0.60, abs=0.001)

    def test_ewma_explicit_negative_lowers_affinity(self):
        result = _ewma(0.5, 0.0, 0.20)
        assert result == pytest.approx(0.40, abs=0.001)

    def test_merge_defaults_fills_missing_keys(self):
        partial = {"provider_affinity": {"openai": 0.7}}
        merged = _merge_defaults(partial)
        assert "response_length_pref" in merged
        assert "observation_counts" in merged
        assert merged["provider_affinity"]["openai"] == 0.7  # existing preserved

    def test_merge_defaults_does_not_overwrite(self):
        profile = _default_profile()
        profile["observation_counts"]["total_responses"] = 42
        merged = _merge_defaults(profile)
        assert merged["observation_counts"]["total_responses"] == 42


# ---------------------------------------------------------------------------
# record_response — EWMA updates
# ---------------------------------------------------------------------------


class TestRecordResponse:
    @pytest.mark.asyncio
    async def test_explicit_positive_raises_provider_affinity(self):
        learner, get_mock, update_mock = _make_learner()
        with (
            patch("api.services.preference_learner.PreferenceLearner.get_profile", get_mock),
            patch(
                "api.storage.preferences_service.PreferencesService.get_learned_preferences",
                get_mock,
            ),
            patch(
                "api.storage.preferences_service.PreferencesService.update_learned_preferences",
                update_mock,
            ),
        ):
            await learner.record_response(
                user_id="u1",
                provider_id="anthropic",
                model="claude-sonnet-4-6",
                intent_label="coding",
                completion_tokens=200,
                explicit_rating=1,
            )

        saved = update_mock.call_args[0][1]
        affinity = saved["provider_affinity"]["anthropic"]
        assert affinity > 0.5, "positive rating should raise affinity above default 0.5"

    @pytest.mark.asyncio
    async def test_explicit_negative_lowers_provider_affinity(self):
        learner, get_mock, update_mock = _make_learner()
        with (
            patch(
                "api.storage.preferences_service.PreferencesService.get_learned_preferences",
                get_mock,
            ),
            patch(
                "api.storage.preferences_service.PreferencesService.update_learned_preferences",
                update_mock,
            ),
        ):
            await learner.record_response(
                user_id="u1",
                provider_id="openai",
                model="gpt-4o",
                intent_label="research",
                completion_tokens=500,
                explicit_rating=-1,
            )

        saved = update_mock.call_args[0][1]
        affinity = saved["provider_affinity"]["openai"]
        assert affinity < 0.5, "negative rating should lower affinity below default 0.5"

    @pytest.mark.asyncio
    async def test_implicit_use_gives_weak_positive_signal(self):
        learner, get_mock, update_mock = _make_learner()
        with (
            patch(
                "api.storage.preferences_service.PreferencesService.get_learned_preferences",
                get_mock,
            ),
            patch(
                "api.storage.preferences_service.PreferencesService.update_learned_preferences",
                update_mock,
            ),
        ):
            await learner.record_response(
                user_id="u1",
                provider_id="deepseek",
                model="deepseek-chat",
                intent_label="coding",
                completion_tokens=300,
                explicit_rating=None,
            )

        saved = update_mock.call_args[0][1]
        affinity = saved["provider_affinity"]["deepseek"]
        # Implicit: 0.95 * 0.5 + 0.05 * 0.7 = 0.51
        assert 0.50 < affinity < 0.55

    @pytest.mark.asyncio
    async def test_response_length_pref_updated_for_concise(self):
        learner, get_mock, update_mock = _make_learner()
        with (
            patch(
                "api.storage.preferences_service.PreferencesService.get_learned_preferences",
                get_mock,
            ),
            patch(
                "api.storage.preferences_service.PreferencesService.update_learned_preferences",
                update_mock,
            ),
        ):
            await learner.record_response(
                user_id="u1",
                provider_id="anthropic",
                model="claude-haiku-4-5",
                intent_label="coding",
                completion_tokens=150,  # concise
                explicit_rating=None,
            )

        saved = update_mock.call_args[0][1]
        assert saved["response_length_pref"]["coding"] == "concise"

    @pytest.mark.asyncio
    async def test_response_length_pref_updated_for_verbose(self):
        learner, get_mock, update_mock = _make_learner()
        with (
            patch(
                "api.storage.preferences_service.PreferencesService.get_learned_preferences",
                get_mock,
            ),
            patch(
                "api.storage.preferences_service.PreferencesService.update_learned_preferences",
                update_mock,
            ),
        ):
            await learner.record_response(
                user_id="u1",
                provider_id="anthropic",
                model="claude-opus-4-8",
                intent_label="research",
                completion_tokens=1200,  # verbose
                explicit_rating=None,
            )

        saved = update_mock.call_args[0][1]
        assert saved["response_length_pref"]["research"] == "verbose"

    @pytest.mark.asyncio
    async def test_response_length_skipped_on_negative_rating(self):
        learner, get_mock, update_mock = _make_learner()
        with (
            patch(
                "api.storage.preferences_service.PreferencesService.get_learned_preferences",
                get_mock,
            ),
            patch(
                "api.storage.preferences_service.PreferencesService.update_learned_preferences",
                update_mock,
            ),
        ):
            await learner.record_response(
                user_id="u1",
                provider_id="openai",
                model="gpt-4o",
                intent_label="coding",
                completion_tokens=1500,  # would be verbose, but response was bad
                explicit_rating=-1,
            )

        saved = update_mock.call_args[0][1]
        # Length pref should NOT be updated when rating is -1
        assert "coding" not in saved.get("response_length_pref", {})

    @pytest.mark.asyncio
    async def test_observation_counts_incremented(self):
        learner, get_mock, update_mock = _make_learner()
        with (
            patch(
                "api.storage.preferences_service.PreferencesService.get_learned_preferences",
                get_mock,
            ),
            patch(
                "api.storage.preferences_service.PreferencesService.update_learned_preferences",
                update_mock,
            ),
        ):
            await learner.record_response(
                user_id="u1",
                provider_id="anthropic",
                model="claude-sonnet-4-6",
                intent_label="finance",
                completion_tokens=400,
                explicit_rating=1,
            )

        saved = update_mock.call_args[0][1]
        counts = saved["observation_counts"]
        assert counts["total_responses"] == 1
        assert counts["explicit_ratings"] == 1
        assert counts["by_intent"]["finance"] == 1

    @pytest.mark.asyncio
    async def test_model_pref_pinned_after_threshold(self):
        existing = _default_profile()
        existing["provider_affinity"]["anthropic"] = 0.85
        existing["observation_counts"]["by_intent"]["coding"] = 5

        learner, get_mock, update_mock = _make_learner(existing)
        with (
            patch(
                "api.storage.preferences_service.PreferencesService.get_learned_preferences",
                get_mock,
            ),
            patch(
                "api.storage.preferences_service.PreferencesService.update_learned_preferences",
                update_mock,
            ),
        ):
            await learner.record_response(
                user_id="u1",
                provider_id="anthropic",
                model="claude-sonnet-4-6",
                intent_label="coding",
                completion_tokens=300,
                explicit_rating=None,
            )

        saved = update_mock.call_args[0][1]
        assert saved["intent_model_pref"].get("coding") == "claude-sonnet-4-6"

    @pytest.mark.asyncio
    async def test_model_pref_not_pinned_below_threshold(self):
        # Affinity is low — should NOT pin the model
        existing = _default_profile()
        existing["provider_affinity"]["openai"] = 0.40
        existing["observation_counts"]["by_intent"]["coding"] = 5

        learner, get_mock, update_mock = _make_learner(existing)
        with (
            patch(
                "api.storage.preferences_service.PreferencesService.get_learned_preferences",
                get_mock,
            ),
            patch(
                "api.storage.preferences_service.PreferencesService.update_learned_preferences",
                update_mock,
            ),
        ):
            await learner.record_response(
                user_id="u1",
                provider_id="openai",
                model="gpt-4o",
                intent_label="coding",
                completion_tokens=300,
                explicit_rating=None,
            )

        saved = update_mock.call_args[0][1]
        assert "coding" not in saved.get("intent_model_pref", {})

    @pytest.mark.asyncio
    async def test_failure_is_swallowed(self):
        """record_response must never raise, even when the DB call fails."""
        learner = PreferenceLearner()
        with patch(
            "api.storage.preferences_service.PreferencesService.get_learned_preferences",
            AsyncMock(side_effect=RuntimeError("DB down")),
        ):
            # Should not raise
            await learner.record_response(
                user_id="u1",
                provider_id="anthropic",
                model=None,
                intent_label="coding",
                completion_tokens=100,
            )


# ---------------------------------------------------------------------------
# apply_to_routing
# ---------------------------------------------------------------------------


class TestApplyToRouting:
    @pytest.mark.asyncio
    async def test_high_affinity_provider_floated_to_front(self):
        profile = _default_profile()
        profile["provider_affinity"] = {"anthropic": 0.85, "openai": 0.40}

        learner = PreferenceLearner()
        with patch.object(learner, "get_profile", AsyncMock(return_value=profile)):
            result = await learner.apply_to_routing("u1", ["openai", "anthropic", "gemini"])

        assert result[0] == "anthropic"
        # openai and gemini remain but anthropic is first
        assert set(result) == {"openai", "anthropic", "gemini"}

    @pytest.mark.asyncio
    async def test_no_affinity_data_returns_original_order(self):
        learner = PreferenceLearner()
        with patch.object(learner, "get_profile", AsyncMock(return_value={})):
            result = await learner.apply_to_routing("u1", ["openai", "anthropic"])

        assert result == ["openai", "anthropic"]

    @pytest.mark.asyncio
    async def test_empty_candidates_returned_unchanged(self):
        learner = PreferenceLearner()
        result = await learner.apply_to_routing("u1", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_no_user_id_returns_unchanged(self):
        learner = PreferenceLearner()
        result = await learner.apply_to_routing("", ["openai", "anthropic"])
        assert result == ["openai", "anthropic"]

    @pytest.mark.asyncio
    async def test_failure_returns_original_order(self):
        learner = PreferenceLearner()
        with patch.object(learner, "get_profile", AsyncMock(side_effect=RuntimeError("boom"))):
            result = await learner.apply_to_routing("u1", ["openai", "anthropic"])

        assert result == ["openai", "anthropic"]

    @pytest.mark.asyncio
    async def test_preserves_relative_order_within_groups(self):
        profile = _default_profile()
        profile["provider_affinity"] = {
            "anthropic": 0.80,
            "gemini": 0.75,
            "openai": 0.30,
        }
        learner = PreferenceLearner()
        with patch.object(learner, "get_profile", AsyncMock(return_value=profile)):
            result = await learner.apply_to_routing(
                "u1", ["openai", "anthropic", "gemini", "deepseek"]
            )

        # Both anthropic and gemini should be in front; openai and deepseek after
        preferred = result[:2]
        rest = result[2:]
        assert set(preferred) == {"anthropic", "gemini"}
        assert set(rest) == {"openai", "deepseek"}


# ---------------------------------------------------------------------------
# get_length_pref
# ---------------------------------------------------------------------------


class TestGetLengthPref:
    @pytest.mark.asyncio
    async def test_returns_stored_pref(self):
        profile = _default_profile()
        profile["response_length_pref"]["coding"] = "concise"

        learner = PreferenceLearner()
        with patch.object(learner, "get_profile", AsyncMock(return_value=profile)):
            result = await learner.get_length_pref("u1", "coding")

        assert result == "concise"

    @pytest.mark.asyncio
    async def test_falls_back_to_default(self):
        learner = PreferenceLearner()
        with patch.object(learner, "get_profile", AsyncMock(return_value={})):
            result = await learner.get_length_pref("u1", "unknown_intent")

        assert result == "medium"

    @pytest.mark.asyncio
    async def test_failure_returns_medium(self):
        learner = PreferenceLearner()
        with patch.object(learner, "get_profile", AsyncMock(side_effect=Exception("boom"))):
            result = await learner.get_length_pref("u1", "coding")

        assert result == "medium"
