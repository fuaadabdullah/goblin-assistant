"""Tests for services/learning_applicator.py — LearningApplicator batch processing."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.services.learning_applicator import (
    _SIGNAL_REWARD,
    _SKIP_SIGNALS,
    LearningApplicator,
    learning_applicator,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _row(
    signal: str = "copy",
    task_type: str = "chat",
    provider: str = "openai",
    user_id: str = "user-1",
    event_id: str = "evt-1",
    message_id: str = "msg-1",
    complexity_score: float = 0.5,
    intent_label: str = "chat",
    model: str = "gpt-4o",
    applied_to_bandit: bool = False,
) -> tuple:
    """Build a (FeedbackEventModel-like, quality_score) tuple as returned by _fetch_unapplied."""
    row = SimpleNamespace(
        event_id=event_id,
        signal=signal,
        task_type=task_type,
        provider=provider,
        user_id=user_id,
        message_id=message_id,
        complexity_score=complexity_score,
        intent_label=intent_label,
        model=model,
        applied_to_bandit=applied_to_bandit,
    )
    return (row, None)  # (row, quality_score)


def _mock_db():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock())
    db.commit = AsyncMock()
    return db


# ── Module constants ──────────────────────────────────────────────────────────


class TestModuleConstants:
    def test_skip_signals_contains_explicit_feedback(self):
        assert "thumbs_up" in _SKIP_SIGNALS
        assert "thumbs_down" in _SKIP_SIGNALS

    def test_signal_reward_contains_expected_signals(self):
        assert "regenerate" in _SIGNAL_REWARD
        assert "delete" in _SIGNAL_REWARD
        assert "copy" in _SIGNAL_REWARD
        assert "continue" in _SIGNAL_REWARD
        assert "provider_switch" in _SIGNAL_REWARD
        assert "model_switch" in _SIGNAL_REWARD

    def test_copy_is_positive_reward(self):
        success, rating = _SIGNAL_REWARD["copy"]
        assert success is True
        assert rating == 1

    def test_delete_is_negative_reward(self):
        success, rating = _SIGNAL_REWARD["delete"]
        assert success is False
        assert rating == -1

    def test_model_switch_is_rating_only(self):
        success, rating = _SIGNAL_REWARD["model_switch"]
        assert success is None
        assert rating == -1


# ── apply_batch ───────────────────────────────────────────────────────────────


class TestApplyBatch:
    @pytest.mark.asyncio
    async def test_empty_rows_returns_zero(self):
        applicator = LearningApplicator()
        db = _mock_db()

        with patch.object(applicator, "_fetch_unapplied", new=AsyncMock(return_value=[])):
            result = await applicator.apply_batch(db)

        assert result == 0

    @pytest.mark.asyncio
    async def test_returns_count_of_processed_rows(self):
        applicator = LearningApplicator()
        db = _mock_db()
        rows = [_row(signal="copy", event_id=f"evt-{i}") for i in range(5)]

        with (
            patch.object(applicator, "_fetch_unapplied", new=AsyncMock(return_value=rows)),
            patch.object(applicator, "_apply_to_bandit"),
            patch.object(applicator, "_apply_to_feature_router"),
            patch.object(applicator, "_apply_to_preference"),
            patch.object(applicator, "_mark_applied", new=AsyncMock()),
        ):
            result = await applicator.apply_batch(db)

        assert result == 5

    @pytest.mark.asyncio
    async def test_skip_signals_not_sent_to_bandit(self):
        applicator = LearningApplicator()
        db = _mock_db()
        rows = [_row(signal="thumbs_up"), _row(signal="thumbs_down")]

        bandit_spy = MagicMock()
        mark_applied = AsyncMock()

        with (
            patch.object(applicator, "_fetch_unapplied", new=AsyncMock(return_value=rows)),
            patch.object(applicator, "_apply_to_bandit", bandit_spy),
            patch.object(applicator, "_mark_applied", new=mark_applied),
        ):
            result = await applicator.apply_batch(db)

        bandit_spy.assert_not_called()
        assert result == 2
        mark_applied.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unknown_signal_marked_applied_without_bandit(self):
        applicator = LearningApplicator()
        db = _mock_db()
        rows = [_row(signal="unknown_mystery_signal")]

        bandit_spy = MagicMock()
        mark_applied = AsyncMock()

        with (
            patch.object(applicator, "_fetch_unapplied", new=AsyncMock(return_value=rows)),
            patch.object(applicator, "_apply_to_bandit", bandit_spy),
            patch.object(applicator, "_mark_applied", new=mark_applied),
        ):
            result = await applicator.apply_batch(db)

        bandit_spy.assert_not_called()
        assert result == 1

    @pytest.mark.asyncio
    async def test_known_signal_calls_all_three_learners(self):
        applicator = LearningApplicator()
        db = _mock_db()
        rows = [_row(signal="copy")]

        bandit_spy = MagicMock()
        feature_spy = MagicMock()
        pref_spy = MagicMock()
        mark_applied = AsyncMock()

        with (
            patch.object(applicator, "_fetch_unapplied", new=AsyncMock(return_value=rows)),
            patch.object(applicator, "_apply_to_bandit", bandit_spy),
            patch.object(applicator, "_apply_to_feature_router", feature_spy),
            patch.object(applicator, "_apply_to_preference", pref_spy),
            patch.object(applicator, "_mark_applied", new=mark_applied),
        ):
            await applicator.apply_batch(db)

        bandit_spy.assert_called_once()
        feature_spy.assert_called_once()
        pref_spy.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_applied_called_with_all_event_ids(self):
        applicator = LearningApplicator()
        db = _mock_db()
        rows = [
            _row(signal="copy", event_id="e1"),
            _row(signal="thumbs_up", event_id="e2"),  # skip signal
            _row(signal="delete", event_id="e3"),
        ]

        captured_ids = []

        async def capture_mark(db, ids):
            captured_ids.extend(ids)

        with (
            patch.object(applicator, "_fetch_unapplied", new=AsyncMock(return_value=rows)),
            patch.object(applicator, "_apply_to_bandit"),
            patch.object(applicator, "_apply_to_feature_router"),
            patch.object(applicator, "_apply_to_preference"),
            patch.object(applicator, "_mark_applied", new=capture_mark),
        ):
            await applicator.apply_batch(db)

        assert set(captured_ids) == {"e1", "e2", "e3"}


# ── _apply_to_bandit ──────────────────────────────────────────────────────────


class TestApplyToBandit:
    def test_no_task_type_skips(self):
        applicator = LearningApplicator()
        row = SimpleNamespace(task_type=None, provider="openai", signal="copy", event_id="e1")
        mock_bandit = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "api.routing.ml_router": MagicMock(bandit_cache=mock_bandit),
            },
        ):
            applicator._apply_to_bandit(row, True, 1)
        mock_bandit.update.assert_not_called()

    def test_no_provider_skips(self):
        applicator = LearningApplicator()
        row = SimpleNamespace(task_type="chat", provider=None, signal="copy", event_id="e1")
        mock_bandit = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "api.routing.ml_router": MagicMock(bandit_cache=mock_bandit),
            },
        ):
            applicator._apply_to_bandit(row, True, 1)
        mock_bandit.update.assert_not_called()

    def test_valid_row_calls_bandit_update(self):
        applicator = LearningApplicator()
        row = SimpleNamespace(task_type="chat", provider="openai", signal="copy", event_id="e1")
        mock_bandit = MagicMock()
        mock_bandit.update.return_value = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "api.routing.ml_router": MagicMock(
                    bandit_cache=mock_bandit,
                    _fire_bandit_state_upsert=MagicMock(),
                ),
                "api.services.outcome_scorer": MagicMock(
                    outcome_scorer=MagicMock(normalize=MagicMock(return_value=0.5))
                ),
            },
        ):
            applicator._apply_to_bandit(row, success=True, rating=1)

        mock_bandit.update.assert_called_once_with("chat", "openai", success=True, rating=1)

    def test_with_quality_score_uses_normalized_rating(self):
        applicator = LearningApplicator()
        row = SimpleNamespace(task_type="chat", provider="openai", signal="copy", event_id="e1")
        mock_bandit = MagicMock()
        mock_bandit.update.return_value = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "api.routing.ml_router": MagicMock(
                    bandit_cache=mock_bandit,
                    _fire_bandit_state_upsert=MagicMock(),
                ),
                "api.services.outcome_scorer": MagicMock(
                    outcome_scorer=MagicMock(normalize=MagicMock(return_value=0.8))
                ),
            },
        ):
            applicator._apply_to_bandit(row, success=True, rating=1, quality_score=8.0)

        # normalized(8.0) = 0.8 → round(0.8 * 2) = 2
        call_kwargs = mock_bandit.update.call_args
        # rating should be overridden to 2 (round(0.8 * 2))
        assert call_kwargs.kwargs.get("rating") == 2

    def test_exception_is_swallowed(self):
        applicator = LearningApplicator()
        row = SimpleNamespace(task_type="chat", provider="openai", signal="copy", event_id="e1")
        with patch.dict(
            "sys.modules",
            {
                "api.routing.ml_router": MagicMock(
                    bandit_cache=MagicMock(update=MagicMock(side_effect=RuntimeError("bang"))),
                    _fire_bandit_state_upsert=MagicMock(),
                ),
                "api.services.outcome_scorer": MagicMock(
                    outcome_scorer=MagicMock(normalize=MagicMock(return_value=0.5))
                ),
            },
        ):
            applicator._apply_to_bandit(row, success=True, rating=1)  # should not raise


# ── _apply_to_feature_router ──────────────────────────────────────────────────


class TestApplyToFeatureRouter:
    def test_success_none_skips(self):
        applicator = LearningApplicator()
        row = SimpleNamespace(
            task_type="chat",
            provider="openai",
            signal="model_switch",
            event_id="e1",
            complexity_score=0.5,
            intent_label="chat",
        )
        mock_fr = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "api.routing.feature_router": MagicMock(feature_router=mock_fr),
            },
        ):
            applicator._apply_to_feature_router(row, success=None, rating=-1)
        mock_fr.record_outcome.assert_not_called()

    def test_no_task_type_skips(self):
        applicator = LearningApplicator()
        row = SimpleNamespace(
            task_type=None,
            provider="openai",
            signal="copy",
            event_id="e1",
            complexity_score=0.5,
            intent_label="chat",
        )
        mock_fr = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "api.routing.feature_router": MagicMock(feature_router=mock_fr),
            },
        ):
            applicator._apply_to_feature_router(row, success=True, rating=1)
        mock_fr.record_outcome.assert_not_called()

    def test_valid_row_calls_feature_router(self):
        applicator = LearningApplicator()
        row = SimpleNamespace(
            task_type="chat",
            provider="openai",
            signal="copy",
            event_id="e1",
            complexity_score=0.5,
            intent_label="chat",
        )
        mock_fr = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "api.routing.feature_router": MagicMock(feature_router=mock_fr),
                "api.routing.router_registry": MagicMock(
                    registry=MagicMock(snapshot=MagicMock(return_value={}))
                ),
                "api.routing.feature_extractor": MagicMock(
                    feature_extractor=MagicMock(extract_providers=MagicMock(return_value={})),
                    RoutingFeatures=MagicMock(return_value=MagicMock()),
                    ProviderFeatures=MagicMock(return_value=MagicMock()),
                ),
            },
        ):
            applicator._apply_to_feature_router(row, success=True, rating=1)

        mock_fr.record_outcome.assert_called_once()

    def test_exception_is_swallowed(self):
        applicator = LearningApplicator()
        row = SimpleNamespace(
            task_type="chat",
            provider="openai",
            signal="copy",
            event_id="e1",
            complexity_score=0.5,
            intent_label="chat",
        )
        with patch.dict(
            "sys.modules",
            {
                "api.routing.feature_router": MagicMock(
                    feature_router=MagicMock(
                        record_outcome=MagicMock(side_effect=RuntimeError("bang"))
                    )
                ),
                "api.routing.router_registry": MagicMock(
                    registry=MagicMock(snapshot=MagicMock(return_value={}))
                ),
                "api.routing.feature_extractor": MagicMock(
                    feature_extractor=MagicMock(extract_providers=MagicMock(return_value={})),
                    RoutingFeatures=MagicMock(return_value=MagicMock()),
                    ProviderFeatures=MagicMock(return_value=MagicMock()),
                ),
            },
        ):
            applicator._apply_to_feature_router(row, success=True, rating=1)  # should not raise


# ── _apply_to_preference ──────────────────────────────────────────────────────


class TestApplyToPreference:
    def test_no_user_id_skips(self):
        applicator = LearningApplicator()
        row = SimpleNamespace(
            user_id=None,
            provider="openai",
            signal="copy",
            model="gpt-4o",
            intent_label="chat",
            task_type="chat",
        )
        mock_pl = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "api.services.preference_learner": MagicMock(preference_learner=mock_pl),
            },
        ):
            applicator._apply_to_preference(row, rating=1)
        mock_pl.record_response.assert_not_called()

    def test_no_provider_skips(self):
        applicator = LearningApplicator()
        row = SimpleNamespace(
            user_id="user-1",
            provider=None,
            signal="copy",
            model="gpt-4o",
            intent_label="chat",
            task_type="chat",
        )
        mock_pl = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "api.services.preference_learner": MagicMock(preference_learner=mock_pl),
            },
        ):
            applicator._apply_to_preference(row, rating=1)
        mock_pl.record_response.assert_not_called()

    def test_exception_is_swallowed(self):
        applicator = LearningApplicator()
        row = SimpleNamespace(
            user_id="user-1",
            provider="openai",
            signal="copy",
            model="gpt-4o",
            intent_label="chat",
            task_type="chat",
        )
        with patch.dict(
            "sys.modules",
            {
                "api.services.preference_learner": MagicMock(
                    preference_learner=MagicMock(
                        record_response=MagicMock(side_effect=RuntimeError("bang"))
                    )
                ),
            },
        ):
            applicator._apply_to_preference(row, rating=1)  # should not raise


# ── _mark_applied ─────────────────────────────────────────────────────────────


class TestMarkApplied:
    @pytest.mark.asyncio
    async def test_calls_execute_and_commit(self):
        applicator = LearningApplicator()
        db = _mock_db()
        await applicator._mark_applied(db, ["e1", "e2"])
        db.execute.assert_awaited_once()
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_ids_still_calls_db(self):
        applicator = LearningApplicator()
        db = _mock_db()
        await applicator._mark_applied(db, [])
        db.execute.assert_awaited_once()


# ── Singleton ─────────────────────────────────────────────────────────────────


def test_learning_applicator_singleton_exists():
    assert learning_applicator is not None
    assert isinstance(learning_applicator, LearningApplicator)
