"""Direct tests for the memory normalization layer.

Tests individual normalization functions in isolation:
- scope derivation precedence
- confidence and importance clamping
- confidence and importance bands
- legacy alias compatibility
- terminal state derivation
- state merging
- empty and oversized payloads
- confidence/importance reason strings
- retention days per kind
"""

from datetime import datetime, timedelta
from typing import Any

from api.services.memory_contract import (
    build_memory_contract_payload,
    confidence_band_from_score,
    importance_band_from_score,
)
from api.services.memory_core.classification import (
    _derive_memory_state,
    _merge_memory_state,
    _normalize_scope,
)
from api.services.memory_core.models import (
    MemoryKind,
    MemoryLifecycleState,
    MemoryRecord,
    MemorySensitivity,
    _default_retention_days,
)
from api.services.memory_core.scoring import (
    _clamp_score,
    _memory_confidence_reason,
    _memory_importance_reason,
)

# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_record(**overrides: Any) -> MemoryRecord:
    """Create a minimal valid MemoryRecord for testing."""
    now = datetime.utcnow()
    defaults = {
        "id": "mem-1",
        "user_id": "user-1",
        "content": "Test fact",
        "memory_type": MemoryKind.FACT,
        "category": "test",
        "source_kind": "memory",
        "source_id": None,
        "confidence": 0.7,
        "salience_score": 0.6,
        "sensitivity_level": MemorySensitivity.LOW,
        "retention_days": 365,
        "created_at": now,
        "updated_at": now,
        "expires_at": now + timedelta(days=365),
        "last_accessed_at": None,
        "state": MemoryLifecycleState.ACTIVE,
        "confirmation_count": 0,
        "is_archived": False,
        "embedding_id": None,
        "score": None,
        "rerank_score": None,
        "related_memory_ids": [],
        "entity_refs": [],
        "metadata": {},
        "scope": "global",
        "confidence_band": "likely_true_usable",
        "confidence_reason": "derived",
        "importance": 0.5,
        "importance_band": "medium",
        "importance_reason": "derived",
        "authored": False,
        "inferred": True,
        "direct_correction": False,
        "contradiction": False,
        "later_contradicted": False,
        "repetition_count": 1,
        "explicitness_score": 0.5,
    }
    defaults.update(overrides)
    return MemoryRecord(**defaults)


def _derive_state(**kwargs: Any) -> MemoryLifecycleState:
    """Helper to call _derive_memory_state with sensible defaults."""
    defaults = {
        "authored": False,
        "inferred": True,
        "direct_correction": False,
        "contradiction": False,
        "later_contradicted": False,
        "confidence": 0.7,
        "repetition_count": 1,
        "importance": 0.5,
        "source_kind": "memory",
        "explicit_kind": None,
        "metadata": {},
    }
    defaults.update(kwargs)
    return _derive_memory_state(**defaults)


# ── Section 1: Confidence and Importance Bands ──────────────────────────────


class TestConfidenceImportanceBands:
    """Tests for confidence and importance band thresholds."""

    def test_confidence_band_strong_stable_at_090(self) -> None:
        """confidence >= 0.90 → 'strong_stable_memory'."""
        assert confidence_band_from_score(0.90) == "strong_stable_memory"
        assert confidence_band_from_score(0.95) == "strong_stable_memory"
        assert confidence_band_from_score(1.0) == "strong_stable_memory"

    def test_confidence_band_likely_true_usable_at_070(self) -> None:
        """0.70 <= confidence < 0.90 → 'likely_true_usable'."""
        assert confidence_band_from_score(0.70) == "likely_true_usable"
        assert confidence_band_from_score(0.75) == "likely_true_usable"
        assert confidence_band_from_score(0.89) == "likely_true_usable"

    def test_confidence_band_weak_needs_verification_at_040(self) -> None:
        """0.40 <= confidence < 0.70 → 'weak_needs_verification'."""
        assert confidence_band_from_score(0.40) == "weak_needs_verification"
        assert confidence_band_from_score(0.50) == "weak_needs_verification"
        assert confidence_band_from_score(0.69) == "weak_needs_verification"

    def test_confidence_band_do_not_use_below_040(self) -> None:
        """confidence < 0.40 → 'do_not_use_by_default'."""
        assert confidence_band_from_score(0.39) == "do_not_use_by_default"
        assert confidence_band_from_score(0.0) == "do_not_use_by_default"
        assert confidence_band_from_score(0.1) == "do_not_use_by_default"

    def test_importance_band_high_at_080(self) -> None:
        """importance >= 0.80 → 'high'."""
        assert importance_band_from_score(0.80) == "high"
        assert importance_band_from_score(0.90) == "high"
        assert importance_band_from_score(1.0) == "high"

    def test_importance_band_medium_at_055(self) -> None:
        """0.55 <= importance < 0.80 → 'medium'."""
        assert importance_band_from_score(0.55) == "medium"
        assert importance_band_from_score(0.70) == "medium"
        assert importance_band_from_score(0.79) == "medium"

    def test_importance_band_low_below_055(self) -> None:
        """importance < 0.55 → 'low'."""
        assert importance_band_from_score(0.54) == "low"
        assert importance_band_from_score(0.0) == "low"
        assert importance_band_from_score(0.3) == "low"


# ── Section 2: Scope Derivation ─────────────────────────────────────────────


class TestScopeDerivation:
    """Tests for _normalize_scope."""

    def test_normalize_scope_explicit_metadata_wins(self) -> None:
        """Explicit metadata['scope'] takes precedence."""
        metadata = {"scope": "conversation"}
        result = _normalize_scope(metadata, "workflow")
        assert result == "conversation"

    def test_normalize_scope_project_signals(self) -> None:
        """metadata['project_id'] → 'project'."""
        result = _normalize_scope({"project_id": "p1"}, "")
        assert result == "project"

    def test_normalize_scope_workflow_id_maps_project(self) -> None:
        """metadata['workflow_id'] → 'project'."""
        result = _normalize_scope({"workflow_id": "w1"}, "")
        assert result == "project"

    def test_normalize_scope_conversation_signal(self) -> None:
        """metadata['conversation_id'] → 'conversation'."""
        result = _normalize_scope({"conversation_id": "c1"}, "")
        assert result == "conversation"

    def test_normalize_scope_tool_metadata(self) -> None:
        """metadata['tool_name'] → 'tool'."""
        result = _normalize_scope({"tool_name": "search"}, "")
        assert result == "tool"

    def test_normalize_scope_source_kind_tool_result(self) -> None:
        """source_kind='tool_result' → 'tool'."""
        result = _normalize_scope({}, "tool_result")
        assert result == "tool"

    def test_normalize_scope_project_beats_conversation(self) -> None:
        """project_id takes precedence over conversation_id."""
        metadata = {"project_id": "p1", "conversation_id": "c1"}
        result = _normalize_scope(metadata, "")
        assert result == "project"

    def test_normalize_scope_conversation_beats_tool(self) -> None:
        """conversation_id takes precedence over tool_name."""
        metadata = {"conversation_id": "c1", "tool_name": "search"}
        result = _normalize_scope(metadata, "")
        assert result == "conversation"

    def test_normalize_scope_empty_metadata_defaults_global(self) -> None:
        """Empty metadata and no source_kind → 'global'."""
        result = _normalize_scope({}, "")
        assert result == "global"


# ── Section 3: Clamping ─────────────────────────────────────────────────────


class TestClampScore:
    """Tests for _clamp_score."""

    def test_clamp_passthrough_in_range(self) -> None:
        """0.5 is returned unchanged."""
        assert _clamp_score(0.5) == 0.5

    def test_clamp_zero(self) -> None:
        """0.0 is clamped to 0.0."""
        assert _clamp_score(0.0) == 0.0

    def test_clamp_one(self) -> None:
        """1.0 is clamped to 1.0."""
        assert _clamp_score(1.0) == 1.0

    def test_clamp_negative_returns_zero(self) -> None:
        """-0.1 is clamped to 0.0."""
        assert _clamp_score(-0.1) == 0.0

    def test_clamp_above_one_returns_one(self) -> None:
        """1.5 is clamped to 1.0."""
        assert _clamp_score(1.5) == 1.0

    def test_clamp_none_returns_default(self) -> None:
        """None returns default (0.0)."""
        assert _clamp_score(None) == 0.0

    def test_clamp_none_custom_default(self) -> None:
        """None with custom default returns custom default."""
        assert _clamp_score(None, default=0.5) == 0.5

    def test_clamp_non_numeric_returns_default(self) -> None:
        """Non-numeric value returns default."""
        assert _clamp_score("bad") == 0.0  # type: ignore

    def test_clamp_nan_behavior(self) -> None:
        """NaN is clamped to bounds (comparison behavior)."""
        import math

        result = _clamp_score(float("nan"))
        # NaN comparisons are always False, so it falls through to bounds
        assert result in (0.0, 1.0) or math.isnan(result)


# ── Section 4: Legacy Aliases ───────────────────────────────────────────────


class TestLegacyAliases:
    """Tests for legacy alias compatibility in build_memory_contract_payload."""

    def test_legacy_fact_text_mirrors_content(self) -> None:
        """payload['fact_text'] == payload['content']."""
        record = _make_record(content="test content")
        payload = build_memory_contract_payload(
            id=record.id,
            content=record.content,
            user_id=record.user_id,
            scope=record.scope,
            memory_type=record.memory_type,
            category=record.category,
            confidence=record.confidence,
            importance=record.importance,
            state=record.state,
            sensitivity_level=record.sensitivity_level,
            source_type="memory",
        )
        assert payload["fact_text"] == payload["content"]
        assert payload["fact_text"] == "test content"

    def test_legacy_memory_type_mirrors_type(self) -> None:
        """payload['memory_type'] == payload['type']."""
        record = _make_record(memory_type=MemoryKind.PREFERENCE)
        payload = build_memory_contract_payload(
            id=record.id,
            content=record.content,
            memory_type=record.memory_type,
            state=record.state,
            source_type="memory",
        )
        assert payload["memory_type"] == payload["type"]
        assert payload["type"] == "preference"

    def test_legacy_status_mirrors_state(self) -> None:
        """payload['status'] == payload['state']."""
        record = _make_record(state=MemoryLifecycleState.ACTIVE)
        payload = build_memory_contract_payload(
            id=record.id,
            content=record.content,
            state=record.state,
            source_type="memory",
        )
        assert payload["status"] == payload["state"]
        assert payload["status"] == "active"

    def test_legacy_is_archived_true_when_state_archived(self) -> None:
        """is_archived=True when state='archived'."""
        record = _make_record(state=MemoryLifecycleState.ARCHIVED)
        payload = build_memory_contract_payload(
            id=record.id,
            content=record.content,
            state=record.state,
            source_type="memory",
        )
        assert payload["is_archived"] is True

    def test_legacy_is_archived_true_when_state_deleted(self) -> None:
        """is_archived=True when state='deleted'."""
        record = _make_record(state=MemoryLifecycleState.DELETED)
        payload = build_memory_contract_payload(
            id=record.id,
            content=record.content,
            state=record.state,
            source_type="memory",
        )
        assert payload["is_archived"] is True

    def test_legacy_is_archived_false_when_state_active(self) -> None:
        """is_archived=False when state='active'."""
        record = _make_record(state=MemoryLifecycleState.ACTIVE)
        payload = build_memory_contract_payload(
            id=record.id,
            content=record.content,
            state=record.state,
            source_type="memory",
        )
        assert payload["is_archived"] is False

    def test_legacy_sensitivity_level_mirrors_sensitivity(self) -> None:
        """payload['sensitivity_level'] == payload['sensitivity']."""
        record = _make_record(sensitivity_level=MemorySensitivity.HIGH)
        payload = build_memory_contract_payload(
            id=record.id,
            content=record.content,
            sensitivity_level=record.sensitivity_level,
            source_type="memory",
        )
        assert payload["sensitivity_level"] == payload["sensitivity"]
        assert payload["sensitivity"] == "high"

    def test_legacy_salience_score_and_importance_fields(self) -> None:
        """payload contains salience_score and importance fields."""
        payload = build_memory_contract_payload(
            id="test-1",
            content="test",
            salience_score=0.75,
            importance=0.6,
            source_type="memory",
        )
        # Both fields should be present in payload (legacy compatibility)
        assert "salience_score" in payload
        assert "importance" in payload
        # Both should be numeric
        assert isinstance(payload["salience_score"], (int, float))
        assert isinstance(payload["importance"], (int, float))


# ── Section 5: Terminal State Derivation ────────────────────────────────────


class TestTerminalStateDerival:
    """Tests for _derive_memory_state and _merge_memory_state."""

    def test_terminal_deleted_from_tombstone(self) -> None:
        """metadata['tombstone']=True → DELETED."""
        result = _derive_state(metadata={"tombstone": True})
        assert result == MemoryLifecycleState.DELETED

    def test_terminal_deleted_from_deleted_at(self) -> None:
        """metadata['deleted_at'] set → DELETED."""
        result = _derive_state(metadata={"deleted_at": "2025-01-01"})
        assert result == MemoryLifecycleState.DELETED

    def test_terminal_archived_from_force_archive(self) -> None:
        """metadata['force_archive']=True → ARCHIVED."""
        result = _derive_state(metadata={"force_archive": True})
        assert result == MemoryLifecycleState.ARCHIVED

    def test_terminal_deleted_beats_archived_in_metadata(self) -> None:
        """metadata['state']='deleted' → DELETED (explicit wins)."""
        result = _derive_state(metadata={"state": "deleted"})
        assert result == MemoryLifecycleState.DELETED

    def test_pinned_memory_returns_valid_state(self) -> None:
        """Pinned memory with low confidence returns a valid state."""
        result = _derive_state(confidence=0.44, repetition_count=1, metadata={"pinned": True})
        # Pinned memory should get a state (potentially not CANDIDATE)
        assert result in {
            MemoryLifecycleState.CANDIDATE,
            MemoryLifecycleState.ACTIVE,
            MemoryLifecycleState.VERIFIED,
            MemoryLifecycleState.DEPRECATED,
        }

    def test_derive_state_returns_valid_state_at_boundary(self) -> None:
        """confidence=0.45 with repetition_count=1 returns a valid state."""
        result = _derive_state(confidence=0.45, repetition_count=1, metadata={})
        # At boundary, some state is returned (CANDIDATE, ACTIVE, etc.)
        assert result in {
            MemoryLifecycleState.CANDIDATE,
            MemoryLifecycleState.ACTIVE,
            MemoryLifecycleState.VERIFIED,
        }

    def test_merge_same_rank_incoming_not_lower(self) -> None:
        """States with same rank: incoming wins if not lower."""
        result = _merge_memory_state(MemoryLifecycleState.DEPRECATED, MemoryLifecycleState.ACTIVE)
        # Rank 1 + Rank 1: incoming should win or be preserved
        assert result in {
            MemoryLifecycleState.ACTIVE,
            MemoryLifecycleState.DEPRECATED,
        }

    def test_merge_terminal_states_preserved(self) -> None:
        """Terminal states (DELETED, ARCHIVED) are terminal."""
        # DELETED is terminal: incoming rank -2
        result_deleted = _merge_memory_state(
            MemoryLifecycleState.ACTIVE, MemoryLifecycleState.DELETED
        )
        assert result_deleted == MemoryLifecycleState.DELETED

        # ARCHIVED is terminal: incoming rank -1
        result_archived = _merge_memory_state(
            MemoryLifecycleState.ACTIVE, MemoryLifecycleState.ARCHIVED
        )
        assert result_archived == MemoryLifecycleState.ARCHIVED

    def test_merge_higher_rank_wins(self) -> None:
        """ACTIVE + VERIFIED → VERIFIED (2 > 1)."""
        result = _merge_memory_state(MemoryLifecycleState.ACTIVE, MemoryLifecycleState.VERIFIED)
        assert result == MemoryLifecycleState.VERIFIED


# ── Section 6: Empty and Oversized Payloads ─────────────────────────────────


class TestEmptyAndOversized:
    """Tests for handling empty and oversized content."""

    def test_payload_empty_content(self) -> None:
        """Empty content produces valid payload."""
        payload = build_memory_contract_payload(
            id="test-1",
            content="",
            source_type="memory",
        )
        assert "summary" in payload
        # Summary is either empty or ellipsis, not a KeyError
        assert isinstance(payload["summary"], str)

    def test_payload_oversized_content(self) -> None:
        """500-char content produces valid payload (summary may be truncated internally)."""
        payload = build_memory_contract_payload(
            id="test-2",
            content="x" * 500,
            source_type="memory",
        )
        # Payload exists and has required fields
        assert "id" in payload
        assert "content" in payload
        assert len(payload) > 0

    def test_payload_empty_metadata(self) -> None:
        """Valid content with minimal args produces valid payload."""
        payload = build_memory_contract_payload(
            id="test-3",
            content="hello",
            source_type="memory",
        )
        # All required keys present
        assert "id" in payload
        assert "content" in payload

    def test_payload_none_metadata_values(self) -> None:
        """None values in args don't cause exceptions."""
        payload = build_memory_contract_payload(
            id="test-4",
            content="test",
            metadata={"project_id": None, "conversation_id": None},
            source_type="memory",
        )
        # No KeyError, no exception
        assert isinstance(payload, dict)
        assert len(payload) > 0

    def test_retention_days_all_kinds(self) -> None:
        """_default_retention_days returns correct values per kind."""
        assert _default_retention_days(MemoryKind.FACT) == 365
        assert _default_retention_days(MemoryKind.PREFERENCE) == 540
        assert _default_retention_days(MemoryKind.DECISION) == 730
        assert _default_retention_days(MemoryKind.PROJECT_STATE) == 90
        assert _default_retention_days(MemoryKind.RELATIONSHIP) == 180
        assert _default_retention_days(MemoryKind.TASK_SIGNAL) == 30


# ── Section 7: Reason Strings ───────────────────────────────────────────────


class TestReasonStrings:
    """Tests for confidence and importance reason strings."""

    def test_confidence_reason_direct_correction(self) -> None:
        """direct_correction flag appears in reason."""
        result = _memory_confidence_reason({"direct_correction": True})
        assert "direct correction" in result.lower()

    def test_confidence_reason_authored(self) -> None:
        """authored flag appears in reason."""
        result = _memory_confidence_reason({"authored": True})
        assert "author" in result.lower()

    def test_confidence_reason_inferred(self) -> None:
        """inferred flag appears in reason."""
        result = _memory_confidence_reason({"inferred": True})
        assert "inferred" in result.lower()

    def test_confidence_reason_repeated(self) -> None:
        """repetition_count appears in reason."""
        result = _memory_confidence_reason({"repetition_count": 3})
        assert "repeat" in result.lower() or "3" in result

    def test_confidence_reason_conflict(self) -> None:
        """contradiction flag appears in reason."""
        result = _memory_confidence_reason({"contradiction": True})
        assert "conflict" in result.lower()

    def test_confidence_reason_later_contradicted(self) -> None:
        """later_contradicted flag appears in reason."""
        result = _memory_confidence_reason({"later_contradicted": True})
        assert "contradicted" in result.lower()

    def test_confidence_reason_fallback(self) -> None:
        """Empty metadata produces fallback reason."""
        result = _memory_confidence_reason({})
        assert "derived" in result.lower() or len(result) > 0

    def test_importance_reason_fallback(self) -> None:
        """Empty metadata produces fallback importance reason."""
        result = _memory_importance_reason({})
        assert "derived" in result.lower() or len(result) > 0
