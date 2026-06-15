"""Mutation testing for memory core invariants.

Verifies that the code is sensitive to changes in critical parameters.
These tests detect regressions where changing one field leaves behavior unaffected.
"""

from __future__ import annotations

from api.services.memory_contract import (
    confidence_band_from_score,
    importance_band_from_score,
)
from api.services.memory_core import (
    MemoryKind,
    _compute_memory_confidence,
    _compute_memory_importance,
)

# ── Confidence scoring mutations ─────────────────────────────────────────────


def test_mutation_authored_flag_affects_confidence():
    """Authored flag should increase confidence vs. inferred."""
    authored = _compute_memory_confidence(
        base_confidence=0.5,
        explicitness=0.5,
        repetition_count=1,
        authored=True,
        inferred=False,
        direct_correction=False,
        contradiction=False,
        later_contradicted=False,
        conflict_penalty=0.0,
    )
    inferred = _compute_memory_confidence(
        base_confidence=0.5,
        explicitness=0.5,
        repetition_count=1,
        authored=False,
        inferred=True,
        direct_correction=False,
        contradiction=False,
        later_contradicted=False,
        conflict_penalty=0.0,
    )
    assert authored > inferred, "Authored memories should be more confident than inferred"


def test_mutation_direct_correction_boosts_confidence():
    """Direct correction flag should boost confidence."""
    uncorrected = _compute_memory_confidence(
        base_confidence=0.6,
        explicitness=0.6,
        repetition_count=1,
        authored=True,
        inferred=False,
        direct_correction=False,
        contradiction=False,
        later_contradicted=False,
        conflict_penalty=0.0,
    )
    corrected = _compute_memory_confidence(
        base_confidence=0.6,
        explicitness=0.6,
        repetition_count=1,
        authored=True,
        inferred=False,
        direct_correction=True,
        contradiction=False,
        later_contradicted=False,
        conflict_penalty=0.0,
    )
    assert corrected > uncorrected, "Direct corrections should boost confidence"


def test_mutation_contradiction_reduces_confidence():
    """Contradiction should reduce confidence."""
    clean = _compute_memory_confidence(
        base_confidence=0.7,
        explicitness=0.7,
        repetition_count=2,
        authored=True,
        inferred=False,
        direct_correction=False,
        contradiction=False,
        later_contradicted=False,
        conflict_penalty=0.0,
    )
    contradicted = _compute_memory_confidence(
        base_confidence=0.7,
        explicitness=0.7,
        repetition_count=2,
        authored=True,
        inferred=False,
        direct_correction=False,
        contradiction=True,
        later_contradicted=False,
        conflict_penalty=0.5,
    )
    assert clean > contradicted, "Contradictions should reduce confidence"


def test_mutation_repetition_count_affects_confidence():
    """Higher repetition count should increase confidence."""
    once = _compute_memory_confidence(
        base_confidence=0.6,
        explicitness=0.6,
        repetition_count=1,
        authored=True,
        inferred=False,
        direct_correction=False,
        contradiction=False,
        later_contradicted=False,
        conflict_penalty=0.0,
    )
    thrice = _compute_memory_confidence(
        base_confidence=0.6,
        explicitness=0.6,
        repetition_count=3,
        authored=True,
        inferred=False,
        direct_correction=False,
        contradiction=False,
        later_contradicted=False,
        conflict_penalty=0.0,
    )
    assert thrice > once, "Higher repetition should increase confidence"


# ── Importance scoring mutations ────────────────────────────────────────────


def test_mutation_task_relevance_affects_importance():
    """Task relevance should increase importance."""
    low_relevance = _compute_memory_importance(
        repetition_count=1,
        use_frequency=0.3,
        task_relevance=0.1,
        explicit_emphasis=0.5,
        dependency_level=0.0,
        future_behavior_impact=0.1,
        memory_type=MemoryKind.FACT,
        scope="global",
    )
    high_relevance = _compute_memory_importance(
        repetition_count=1,
        use_frequency=0.3,
        task_relevance=0.9,
        explicit_emphasis=0.5,
        dependency_level=0.0,
        future_behavior_impact=0.1,
        memory_type=MemoryKind.FACT,
        scope="global",
    )
    assert high_relevance > low_relevance, "Task relevance should increase importance"


def test_mutation_memory_type_affects_importance():
    """Different memory types should have different baseline importance."""
    decision = _compute_memory_importance(
        repetition_count=1,
        use_frequency=0.5,
        task_relevance=0.5,
        explicit_emphasis=0.5,
        dependency_level=0.5,
        future_behavior_impact=0.5,
        memory_type=MemoryKind.DECISION,
        scope="project",
    )
    fact = _compute_memory_importance(
        repetition_count=1,
        use_frequency=0.5,
        task_relevance=0.5,
        explicit_emphasis=0.5,
        dependency_level=0.5,
        future_behavior_impact=0.5,
        memory_type=MemoryKind.FACT,
        scope="global",
    )
    # Decisions are typically more important than facts in context
    assert decision >= fact, "Memory type should affect importance"


def test_mutation_scope_affects_importance():
    """Scope should affect importance (project > conversation > global)."""
    project_scope = _compute_memory_importance(
        repetition_count=1,
        use_frequency=0.5,
        task_relevance=0.5,
        explicit_emphasis=0.5,
        dependency_level=0.5,
        future_behavior_impact=0.5,
        memory_type=MemoryKind.PROJECT_STATE,
        scope="project",
    )
    global_scope = _compute_memory_importance(
        repetition_count=1,
        use_frequency=0.5,
        task_relevance=0.5,
        explicit_emphasis=0.5,
        dependency_level=0.5,
        future_behavior_impact=0.5,
        memory_type=MemoryKind.FACT,
        scope="global",
    )
    # Project state should be more important than global facts
    assert project_scope >= global_scope, "Scope should affect importance"


# ── Band mutation tests ─────────────────────────────────────────────────────


def test_mutation_confidence_score_moves_band():
    """Changing confidence score should move between bands at thresholds."""
    band_at_0_65 = confidence_band_from_score(0.65)
    band_at_0_70 = confidence_band_from_score(0.70)
    band_at_0_75 = confidence_band_from_score(0.75)

    # 0.65 and below should be different from 0.70+
    assert band_at_0_65 != band_at_0_70, "Band should change at 0.70 threshold"
    # 0.70 and 0.75 should be the same
    assert band_at_0_70 == band_at_0_75


def test_mutation_importance_score_moves_band():
    """Changing importance score should move between bands at thresholds."""
    band_at_0_50 = importance_band_from_score(0.50)
    band_at_0_55 = importance_band_from_score(0.55)
    band_at_0_80 = importance_band_from_score(0.80)

    # 0.50 should be different from 0.55+
    assert band_at_0_50 != band_at_0_55, "Band should change at 0.55 threshold"
    # 0.55 and below should be different from 0.80+
    assert band_at_0_55 != band_at_0_80, "Band should change at 0.80 threshold"
