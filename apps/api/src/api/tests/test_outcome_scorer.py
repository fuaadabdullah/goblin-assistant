"""Tests for outcome_scorer and quality_score accumulation in LearningApplicator."""

from unittest.mock import MagicMock, patch

import pytest

from api.services.outcome_scorer import _SIGNAL_POINTS, outcome_scorer

# ── OutcomeScorer unit tests ──────────────────────────────────────────────────


class TestOutcomeScorerPoints:
    def test_all_signal_points_present(self):
        expected = {
            "thumbs_up",
            "copy",
            "continue",
            "model_switch",
            "regenerate",
            "delete",
            "provider_switch",
            "thumbs_down",
        }
        assert set(_SIGNAL_POINTS.keys()) == expected

    def test_positive_signals(self):
        assert outcome_scorer.points_for("thumbs_up") == 5
        assert outcome_scorer.points_for("copy") == 3
        assert outcome_scorer.points_for("continue") == 2

    def test_negative_signals(self):
        assert outcome_scorer.points_for("provider_switch") == -5
        assert outcome_scorer.points_for("thumbs_down") == -5
        assert outcome_scorer.points_for("delete") == -4
        assert outcome_scorer.points_for("regenerate") == -3
        assert outcome_scorer.points_for("model_switch") == -2

    def test_unknown_signal_returns_zero(self):
        assert outcome_scorer.points_for("unknown_signal") == 0
        assert outcome_scorer.points_for("") == 0
        assert outcome_scorer.points_for("hover") == 0


class TestOutcomeScorerNormalize:
    def test_zero_maps_to_zero(self):
        assert outcome_scorer.normalize(0.0) == pytest.approx(0.0)

    def test_positive_ten_maps_to_one(self):
        assert outcome_scorer.normalize(10.0) == pytest.approx(1.0)

    def test_negative_ten_maps_to_minus_one(self):
        assert outcome_scorer.normalize(-10.0) == pytest.approx(-1.0)

    def test_clamped_above_ten(self):
        assert outcome_scorer.normalize(20.0) == pytest.approx(1.0)
        assert outcome_scorer.normalize(100.0) == pytest.approx(1.0)

    def test_clamped_below_minus_ten(self):
        assert outcome_scorer.normalize(-20.0) == pytest.approx(-1.0)

    def test_proportional_midpoint(self):
        assert outcome_scorer.normalize(5.0) == pytest.approx(0.5)
        assert outcome_scorer.normalize(-5.0) == pytest.approx(-0.5)

    def test_thumbs_up_plus_continue_accumulates(self):
        quality = outcome_scorer.points_for("thumbs_up") + outcome_scorer.points_for("continue")
        assert quality == 7
        assert outcome_scorer.normalize(quality) == pytest.approx(0.7)

    def test_copy_then_regenerate_nets_zero(self):
        quality = outcome_scorer.points_for("copy") + outcome_scorer.points_for("regenerate")
        assert quality == 0
        assert outcome_scorer.normalize(quality) == pytest.approx(0.0)


# ── LearningApplicator uses quality_score for proportional bandit rating ──────


@pytest.mark.asyncio
async def test_learning_applicator_uses_quality_score_for_bandit():
    """When quality_score is available, bandit gets proportional rating, not ±1."""
    from api.services.learning_applicator import LearningApplicator

    applicator = LearningApplicator()

    captured_rating = {}

    def fake_bandit_update(task_type, provider_id, *, success, rating=None):
        captured_rating["rating"] = rating
        state = MagicMock()
        state.alpha = 1.0
        state.beta = 1.0
        return state

    # Row with regenerate signal and a positive quality_score (mixed message)
    row = MagicMock()
    row.task_type = "coding"
    row.provider = "anthropic"
    row.signal = "regenerate"

    quality_score = 8.0  # net positive despite this one regenerate event

    with patch.dict(
        "sys.modules",
        {
            "api.routing.ml_router": MagicMock(
                bandit_cache=MagicMock(update=fake_bandit_update),
                _fire_bandit_state_upsert=MagicMock(),
            )
        },
    ):
        applicator._apply_to_bandit(row, False, -1, quality_score)

    assert (
        captured_rating.get("rating") == 2
    )  # quality 8 normalizes to 0.8, scaled to ±2 range rounds to 2


@pytest.mark.asyncio
async def test_learning_applicator_falls_back_to_binary_when_no_quality_score():
    """When quality_score is None (no message_outcomes row), use ±1 from _SIGNAL_REWARD."""
    from api.services.learning_applicator import LearningApplicator

    applicator = LearningApplicator()
    captured_rating = {}

    def fake_bandit_update(task_type, provider_id, *, success, rating=None):
        captured_rating["rating"] = rating
        return MagicMock(alpha=1.0, beta=1.0)

    row = MagicMock()
    row.task_type = "coding"
    row.provider = "anthropic"
    row.signal = "copy"

    with patch.dict(
        "sys.modules",
        {
            "api.routing.ml_router": MagicMock(
                bandit_cache=MagicMock(update=fake_bandit_update),
                _fire_bandit_state_upsert=MagicMock(),
            )
        },
    ):
        applicator._apply_to_bandit(row, True, +1, quality_score=None)

    assert captured_rating.get("rating") == 1
