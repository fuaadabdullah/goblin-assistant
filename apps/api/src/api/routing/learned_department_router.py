"""
Learned department router — replaces INTENT_TO_DEPARTMENT dict with a
trained probability model.

The model is a per-department linear scorer: for each department, compute a
dot product between the feature vector and learned weights, then softmax over
all departments.  Weights are seeded from the rule-based mapping on first
startup and updated online from user feedback (thumbs-up/down) via the same
perceptron-style gradient used by feature_router.py.

Data flow:
    select(features) → (DepartmentId, confidence)
    record_outcome(features, department, success, rating) → gradient update
    load_weights()   → restore from Supabase department_routing_weights
    _fire_upsert()   → fire-and-forget write to Supabase
"""

from __future__ import annotations

import logging
import math
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .feature_extractor import RoutingFeatures

logger = logging.getLogger(__name__)

# Set DEPARTMENT_ROUTER_LIVE=true to use learned picks for actual routing.
# When false (default), the rule-based mapping is still used but the learned
# router's choice is shadow-logged for validation.
_LIVE = os.getenv("DEPARTMENT_ROUTER_LIVE", "false").lower() in ("true", "1", "yes")

_SOFTMAX_TEMPERATURE = 1.5  # higher → flatter distribution (more exploration)
_MIN_OBS_FOR_EXPLOITATION = 10  # minimum observations before learned scores are trusted


# ---------------------------------------------------------------------------
# Department IDs — mirrored here to avoid a circular import
# ---------------------------------------------------------------------------

_DEPARTMENT_IDS = [
    "reasoning",
    "coding",
    "creative",
    "recall",
    "tool_use",
    "research",
    "general",
]

# Seed weights: for each department, a mapping of feature_name → initial weight.
# These encode the rule-based intent→department mapping as soft priors.
_SEED_WEIGHTS: Dict[str, Dict[str, float]] = {
    "reasoning": {
        "intent_reasoning": 2.0,
        "intent_logic": 2.0,
        "intent_analysis": 1.5,
        "intent_planning": 1.5,
        "intent_math": 1.5,
        "complexity": 1.0,
    },
    "coding": {
        "intent_coding": 2.0,
        "intent_code_generation": 2.0,
        "intent_debugging": 2.0,
        "intent_refactoring": 1.5,
        "intent_code_review": 1.5,
    },
    "creative": {
        "intent_creative": 2.0,
        "intent_writing": 2.0,
        "intent_brainstorming": 1.5,
        "intent_content_creation": 1.5,
    },
    "recall": {
        "intent_recall": 2.0,
        "intent_memory": 2.0,
        "intent_retrieval": 1.5,
        "intent_context_query": 1.5,
        "retrieval_prob": 1.5,
        "latency_sensitivity": 0.5,
    },
    "tool_use": {
        "intent_tool_use": 2.0,
        "intent_function_calling": 2.0,
        "intent_action": 1.5,
        "intent_automation": 1.5,
        "tool_prob": 2.0,
    },
    "research": {
        "intent_research": 2.0,
        "intent_deep_research": 2.0,
        "intent_investigation": 1.5,
        "intent_synthesis": 1.5,
        "retrieval_prob": 1.0,
        "complexity": 0.5,
        "prompt_length": 0.5,
    },
    "general": {
        "bias": 0.5,  # small positive bias so GENERAL wins when no other signal fires
    },
}


# ---------------------------------------------------------------------------
# Per-department weight state
# ---------------------------------------------------------------------------


@dataclass
class DeptWeights:
    department_id: str
    weights: Dict[str, float] = field(default_factory=dict)
    observation_count: int = 0
    last_updated_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Feature vector builder
# ---------------------------------------------------------------------------


def _feature_vector(features: RoutingFeatures) -> Dict[str, float]:
    """Convert RoutingFeatures into a named feature dict for the scorer."""
    vec: Dict[str, float] = {
        "prompt_length": features.prompt_length_bucket / 3.0,
        "complexity": features.complexity_score,
        "intent_confidence": features.intent_confidence,
        "retrieval_prob": features.retrieval_probability,
        "tool_prob": features.tool_probability,
        "latency_sensitivity": features.latency_sensitivity,
        "turn_depth": features.conversation_turn / 10.0,
        "bias": 1.0,
    }
    # One-hot intent label
    if features.intent_label and features.intent_label != "unknown":
        vec[f"intent_{features.intent_label}"] = 1.0
    return vec


def _dot(weights: Dict[str, float], vec: Dict[str, float]) -> float:
    return sum(weights.get(k, 0.0) * v for k, v in vec.items())


def _softmax(scores: Dict[str, float], temperature: float = 1.0) -> Dict[str, float]:
    scaled = {k: v / temperature for k, v in scores.items()}
    max_v = max(scaled.values())
    exps = {k: math.exp(v - max_v) for k, v in scaled.items()}
    total = sum(exps.values()) or 1.0
    return {k: exps[k] / total for k in scaled}


# ---------------------------------------------------------------------------
# LearnedDepartmentRouter
# ---------------------------------------------------------------------------


class LearnedDepartmentRouter:
    """
    Online linear department classifier.

    Scores each department with a dot product over the feature vector,
    soft-maxes the result, and returns the winning department with its
    confidence.  Weights are updated via a perceptron gradient after each
    user feedback signal.
    """

    def __init__(self) -> None:
        self._weights: Dict[str, DeptWeights] = {}
        self._bootstrapped = False
        # request_id → (feature_vec, department_id) for pending feedback attribution
        self._pending: Dict[str, Tuple[Dict[str, float], str]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def select(
        self,
        features: RoutingFeatures,
        *,
        request_id: Optional[str] = None,
    ) -> Tuple[str, float]:
        """Return (department_id, confidence) for the given features.

        Confidence is the softmax probability of the winning department.
        Before enough training data exists (_MIN_OBS_FOR_EXPLOITATION),
        the model still returns scores but they are close to the seeded priors.
        """
        self._ensure_bootstrapped()
        vec = _feature_vector(features)
        raw_scores = {d: _dot(self._weights[d].weights, vec) for d in _DEPARTMENT_IDS}
        probs = _softmax(raw_scores, temperature=_SOFTMAX_TEMPERATURE)
        winner = max(probs, key=lambda d: probs[d])
        confidence = round(probs[winner], 4)

        if request_id and len(self._pending) < 10_000:
            self._pending[request_id] = (vec, winner)

        return winner, confidence

    def record_outcome(
        self,
        *,
        features: Optional[RoutingFeatures] = None,
        feature_vec: Optional[Dict[str, float]] = None,
        department_id: str,
        success: bool,
        rating: Optional[int] = None,
    ) -> None:
        """Gradient-update the weights for the chosen department.

        Supply either features or a pre-built feature_vec.
        """
        self._ensure_bootstrapped()
        vec = (
            feature_vec
            if feature_vec is not None
            else (_feature_vector(features) if features is not None else {})
        )
        if not vec:
            return

        w = self._get_weights(department_id)
        obs = w.observation_count
        lr = max(0.02, 0.3 / (1.0 + obs * 0.01))

        raw_scores = {d: _dot(self._weights[d].weights, vec) for d in _DEPARTMENT_IDS}
        probs = _softmax(raw_scores, temperature=_SOFTMAX_TEMPERATURE)
        predicted = probs.get(department_id, 0.0)

        actual = 1.0 if success else 0.0
        if rating is not None:
            actual += 0.25 * rating  # ±0.25 for thumbs up/down
        actual = max(0.0, min(1.25, actual))

        error = actual - predicted
        for feat_name, feat_val in vec.items():
            old = w.weights.get(feat_name, 0.0)
            w.weights[feat_name] = round(max(-5.0, min(5.0, old + lr * error * feat_val)), 6)

        w.observation_count += 1
        w.last_updated_at = time.time()

        _fire_dept_weights_upsert(department_id, w.weights, w.observation_count)

    def record_outcome_by_request_id(
        self,
        *,
        request_id: str,
        department_id: str,
        success: bool,
        rating: Optional[int] = None,
    ) -> bool:
        """Apply outcome using features cached at select() time.

        Returns True if the request_id was found in the pending cache.
        """
        entry = self._pending.pop(request_id, None)
        if entry is None:
            return False
        vec, _original_dept = entry
        self.record_outcome(
            feature_vec=vec,
            department_id=department_id,
            success=success,
            rating=rating,
        )
        return True

    @property
    def is_live(self) -> bool:
        return _LIVE

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def load_weights(self) -> None:
        """Restore weights from Supabase department_routing_weights table."""
        try:
            from api.providers.supabase_events import (  # noqa: PLC0415
                _ENABLED,
                _HEADERS,
                _REST,
                _get_client,
            )

            if not _ENABLED:
                return

            resp = await _get_client().get(
                f"{_REST}/department_routing_weights",
                headers={**_HEADERS, "Accept": "application/json"},
                params={"select": "department_id,feature_name,weight,observation_count"},
            )
            rows = resp.json() if resp.status_code == 200 else []
            if not isinstance(rows, list) or not rows:
                logger.info("department_router_no_saved_weights_found")
                return

            # Group by department
            by_dept: Dict[str, Dict[str, float]] = {}
            obs_by_dept: Dict[str, int] = {}
            for row in rows:
                dept = str(row.get("department_id", ""))
                feat = str(row.get("feature_name", ""))
                weight = float(row.get("weight", 0.0))
                obs = int(row.get("observation_count", 0))
                if dept and feat:
                    by_dept.setdefault(dept, {})[feat] = weight
                    obs_by_dept[dept] = max(obs_by_dept.get(dept, 0), obs)

            for dept_id, weights in by_dept.items():
                if dept_id in _DEPARTMENT_IDS:
                    w = self._get_weights(dept_id)
                    w.weights.update(weights)
                    w.observation_count = obs_by_dept.get(dept_id, 0)

            self._bootstrapped = True
            logger.info("department_router_weights_restored departments=%d", len(by_dept))
        except Exception as exc:
            logger.warning("department_router_weights_restore_failed error=%s", exc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_bootstrapped(self) -> None:
        if not self._bootstrapped:
            self._bootstrap_from_rules()

    def _bootstrap_from_rules(self) -> None:
        """Seed weights from _SEED_WEIGHTS so day-1 behavior matches the rules."""
        for dept_id in _DEPARTMENT_IDS:
            w = self._get_weights(dept_id)
            if not w.weights:
                w.weights = dict(_SEED_WEIGHTS.get(dept_id, {}))
        self._bootstrapped = True
        logger.info("department_router_bootstrapped_from_rules")

    def _get_weights(self, department_id: str) -> DeptWeights:
        if department_id not in self._weights:
            self._weights[department_id] = DeptWeights(department_id=department_id)
        return self._weights[department_id]


# ---------------------------------------------------------------------------
# Supabase persistence — fire-and-forget
# ---------------------------------------------------------------------------


def _fire_dept_weights_upsert(
    department_id: str, weights: Dict[str, float], observation_count: int
) -> None:
    try:
        from api.providers.supabase_events import (  # noqa: PLC0415
            _HEADERS,
            _REST,
            _fire,
            _get_client,
        )

        rows: List[Dict] = [
            {
                "department_id": department_id,
                "feature_name": feat,
                "weight": weight,
                "observation_count": observation_count,
                "last_updated_at": "now()",
            }
            for feat, weight in weights.items()
        ]

        async def _upsert() -> None:
            if not _REST or not rows:
                return
            try:
                await _get_client().post(
                    f"{_REST}/department_routing_weights",
                    headers={
                        **_HEADERS,
                        "Prefer": "resolution=merge-duplicates,return=minimal",
                    },
                    json=rows,
                )
            except Exception as exc:
                logger.debug("dept_weights_upsert_failed error=%s", exc)

        _fire(_upsert())
    except Exception as exc:
        logger.debug("dept_weights_upsert_schedule_failed error=%s", exc)


# Module singleton
learned_department_router = LearnedDepartmentRouter()
