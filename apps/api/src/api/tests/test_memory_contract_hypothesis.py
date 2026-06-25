"""Property-based tests for memory band scoring.

This file stays narrow on monotonic score-band invariants and does not test
contract assembly behavior.
"""

from __future__ import annotations

import pytest

from api.services.memory_contract import (
    confidence_band_from_score,
    importance_band_from_score,
)

try:
    from hypothesis import given
    from hypothesis import strategies as st

    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False

    def given(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    st = None


if HAS_HYPOTHESIS:

    @st.composite
    def score_strategy(draw: st.DrawFn) -> float:
        return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))

    @given(score_strategy())
    def test_confidence_band_always_returns_valid_band(score: float):
        band = confidence_band_from_score(score)
        assert band in {
            "strong_stable_memory",
            "likely_true_usable",
            "weak_needs_verification",
            "do_not_use_by_default",
        }

    @given(score_strategy())
    def test_importance_band_always_returns_valid_band(score: float):
        band = importance_band_from_score(score)
        assert band in {"high", "medium", "low"}

    @given(score_strategy())
    def test_confidence_band_is_monotonic(score: float):
        band_rank = {
            "do_not_use_by_default": 0,
            "weak_needs_verification": 1,
            "likely_true_usable": 2,
            "strong_stable_memory": 3,
        }

        band_at_score = confidence_band_from_score(score)
        band_at_higher = confidence_band_from_score(min(1.0, score + 0.01))

        assert band_rank[band_at_score] <= band_rank[band_at_higher]

    @given(score_strategy())
    def test_importance_band_is_monotonic(score: float):
        band_rank = {"low": 0, "medium": 1, "high": 2}

        band_at_score = importance_band_from_score(score)
        band_at_higher = importance_band_from_score(min(1.0, score + 0.01))

        assert band_rank[band_at_score] <= band_rank[band_at_higher]
else:

    def test_hypothesis_skipped():
        pytest.skip("hypothesis not installed")
