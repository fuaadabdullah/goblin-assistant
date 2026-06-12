"""Scoring algorithms for memory confidence, importance, and salience."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import MemoryKind


def _clamp_score(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _compute_salience(
    *,
    created_at: datetime,
    confidence: float,
    repetition_count: int,
    active_context: bool,
    user_importance: float,
    memory_type: MemoryKind,
) -> float:
    now = datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (now - created_at).total_seconds() / 86400.0)
    recency = pow(0.985, age_days)
    repetition = min(1.0, 0.25 * max(repetition_count, 1))
    kind_boost = {
        MemoryKind.PREFERENCE: 0.12,
        MemoryKind.DECISION: 0.15,
        MemoryKind.PROJECT_STATE: 0.10,
        MemoryKind.RELATIONSHIP: 0.08,
        MemoryKind.TASK_SIGNAL: 0.06,
        MemoryKind.FACT: 0.10,
    }[memory_type]
    active_boost = 0.12 if active_context else 0.0
    score = (
        0.38 * max(0.0, min(confidence, 1.0))
        + 0.27 * recency
        + 0.15 * repetition
        + 0.10 * max(0.0, min(user_importance, 1.0))
        + kind_boost
        + active_boost
    )
    return max(0.0, min(score, 1.0))


def _derive_explicitness_score(text: str, metadata: Dict[str, Any]) -> float:
    if metadata.get("explicitness_score") is not None:
        return _clamp_score(metadata.get("explicitness_score"), 0.5)
    if metadata.get("is_explicit") is True:
        return 0.95
    if metadata.get("is_explicit") is False:
        return 0.45
    if any(token in text.lower() for token in ("i prefer", "i want", "remember", "please remember")):
        return 0.9
    return 0.65


def _memory_confidence_reason(metadata: Dict[str, Any]) -> str:
    reasons: List[str] = []
    if metadata.get("direct_correction"):
        reasons.append("direct correction")
    if metadata.get("authored"):
        reasons.append("user-authored")
    if metadata.get("inferred"):
        reasons.append("inferred")
    if metadata.get("repetition_count", 0):
        reasons.append(f"repeated {int(metadata.get('repetition_count', 0))}x")
    if metadata.get("conflicts_with_existing") or metadata.get("contradiction"):
        reasons.append("conflict detected")
    if metadata.get("later_contradicted"):
        reasons.append("later contradicted")
    if metadata.get("explicitness_score") is not None:
        reasons.append(f"explicitness {float(metadata.get('explicitness_score', 0.0)):.2f}")
    return "; ".join(reasons) if reasons else "derived from write-time signals"


def _memory_importance_reason(metadata: Dict[str, Any]) -> str:
    reasons: List[str] = []
    if metadata.get("use_frequency") is not None:
        reasons.append(f"use frequency {float(metadata.get('use_frequency', 0.0)):.2f}")
    if metadata.get("task_relevance") is not None:
        reasons.append(f"task relevance {float(metadata.get('task_relevance', 0.0)):.2f}")
    if metadata.get("user_importance") is not None:
        reasons.append(f"user emphasis {float(metadata.get('user_importance', 0.0)):.2f}")
    if metadata.get("dependency_level") is not None:
        reasons.append(f"dependency {float(metadata.get('dependency_level', 0.0)):.2f}")
    if metadata.get("future_behavior_impact") is not None:
        reasons.append(
            f"future impact {float(metadata.get('future_behavior_impact', 0.0)):.2f}"
        )
    return "; ".join(reasons) if reasons else "derived from frequency, relevance, and impact"


def _compute_memory_confidence(
    *,
    base_confidence: float,
    explicitness: float,
    repetition_count: int,
    authored: bool,
    inferred: bool,
    direct_correction: bool,
    contradiction: bool,
    later_contradicted: bool,
    conflict_penalty: float,
) -> float:
    repetition_factor = min(1.0, 0.35 * max(repetition_count, 1))
    provenance_score = 1.0 if authored else 0.45 if inferred else 0.65
    score = 0.35 * _clamp_score(base_confidence, 0.5)
    score += 0.25 * _clamp_score(explicitness, 0.5)
    score += 0.15 * repetition_factor
    score += 0.15 * provenance_score
    score += 0.10 * (1.0 if direct_correction else 0.0)
    score -= 0.18 * _clamp_score(conflict_penalty, 0.0)
    score -= 0.15 * (1.0 if contradiction else 0.0)
    score -= 0.15 * (1.0 if later_contradicted else 0.0)
    return max(0.0, min(score, 1.0))


def _compute_memory_importance(
    *,
    repetition_count: int,
    use_frequency: Optional[float],
    task_relevance: Optional[float],
    explicit_emphasis: Optional[float],
    dependency_level: Optional[float],
    future_behavior_impact: Optional[float],
    memory_type: MemoryKind,
    scope: str,
) -> float:
    frequency_score = _clamp_score(
        use_frequency if use_frequency is not None else min(1.0, 0.2 * max(repetition_count, 1)),
        0.0,
    )
    task_score = _clamp_score(
        task_relevance
        if task_relevance is not None
        else (
            0.9
            if memory_type in {MemoryKind.PROJECT_STATE, MemoryKind.DECISION, MemoryKind.TASK_SIGNAL}
            else 0.6
        ),
        0.0,
    )
    emphasis_score = _clamp_score(
        explicit_emphasis if explicit_emphasis is not None else 0.5 + 0.1 * max(repetition_count - 1, 0),
        0.5,
    )
    dependency_score = _clamp_score(
        dependency_level if dependency_level is not None else (0.8 if scope == "project" else 0.3),
        0.0,
    )
    impact_score = _clamp_score(
        future_behavior_impact
        if future_behavior_impact is not None
        else (0.85 if memory_type in {MemoryKind.PREFERENCE, MemoryKind.PROJECT_STATE} else 0.45),
        0.0,
    )
    score = (
        0.25 * frequency_score
        + 0.25 * task_score
        + 0.20 * emphasis_score
        + 0.15 * dependency_score
        + 0.15 * impact_score
    )
    return max(0.0, min(score, 1.0))
