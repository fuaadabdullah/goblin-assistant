"""Per-message quality scoring from accumulated feedback signals.

Each feedback signal on a message adds or subtracts points from a running
quality_score stored in message_outcomes. The score is used by the
LearningApplicator to pass a proportional float reward to the bandit instead
of a fixed binary ±1.

    copy:            +3  (user found it useful)
    thumbs_up:       +5  (explicit approval)
    continue:        +2  (conversation kept going — weak positive)
    model_switch:    -2  (ambiguous — slightly negative)
    regenerate:      -3  (user tried again)
    delete:          -4  (user removed the response)
    provider_switch: -5  (voted against the provider with their feet)
    thumbs_down:     -5  (explicit rejection)
"""

from __future__ import annotations

_SIGNAL_POINTS: dict[str, int] = {
    "thumbs_up": +5,
    "copy": +3,
    "continue": +2,
    "model_switch": -2,
    "regenerate": -3,
    "delete": -4,
    "provider_switch": -5,
    "thumbs_down": -5,
}


class OutcomeScorer:
    """Translates signal names to point values and normalizes for ML consumption."""

    def points_for(self, signal: str) -> int:
        """Return the point delta for a given signal. Unknown signals → 0."""
        return _SIGNAL_POINTS.get(signal, 0)

    def normalize(self, quality_score: float) -> float:
        """Map an accumulated quality score to [-1.0, +1.0] for bandit/feature-router.

        Uses a ±10 scale: quality=+10 → +1.0, quality=-10 → -1.0.
        Scores outside this range are clamped.
        """
        return max(-1.0, min(1.0, quality_score / 10.0))


outcome_scorer = OutcomeScorer()
