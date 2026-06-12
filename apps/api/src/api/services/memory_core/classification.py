"""Heuristics for classifying memory type, scope, state, and sensitivity."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..sanitization import is_sensitive_content
from .models import MemoryKind, MemoryLifecycleState, MemorySensitivity, _safe_memory_state


def _is_pinned(metadata: Dict[str, Any]) -> bool:
    return bool(metadata.get("pinned") or metadata.get("is_pinned") or metadata.get("manual_pin"))


def _merge_memory_state(
    current: Optional[str],
    incoming: MemoryLifecycleState,
) -> MemoryLifecycleState:
    current_state = _safe_memory_state(current)
    if incoming in {MemoryLifecycleState.DELETED, MemoryLifecycleState.ARCHIVED}:
        return incoming
    if current_state in {MemoryLifecycleState.DELETED, MemoryLifecycleState.ARCHIVED}:
        return current_state
    from .models import _state_rank  # noqa: PLC0415

    if _state_rank(incoming) >= _state_rank(current_state):
        return incoming
    return current_state


def _derive_memory_state(
    *,
    metadata: Dict[str, Any],
    confidence: float,
    repetition_count: int,
    authored: bool,
    inferred: bool,
    direct_correction: bool,
    contradiction: bool,
    later_contradicted: bool,
    importance: float,
    source_kind: str,
    explicit_kind: Optional[str],
) -> MemoryLifecycleState:
    hinted = metadata.get("memory_state") or metadata.get("state")
    if hinted:
        return _safe_memory_state(str(hinted))
    if metadata.get("deleted") or metadata.get("deleted_at") or metadata.get("tombstone"):
        return MemoryLifecycleState.DELETED
    if metadata.get("archive_requested") or metadata.get("force_archive"):
        return MemoryLifecycleState.ARCHIVED
    if direct_correction or metadata.get("verified") is True:
        return MemoryLifecycleState.VERIFIED
    if contradiction or later_contradicted:
        return MemoryLifecycleState.DEPRECATED
    if not _is_pinned(metadata) and (confidence < 0.45 or repetition_count < 2):
        return MemoryLifecycleState.CANDIDATE
    if not inferred and authored and confidence >= 0.9 and repetition_count >= 2:
        return MemoryLifecycleState.VERIFIED
    if (
        importance >= 0.8
        or source_kind in {"memory", "conversation"}
        or explicit_kind
        in {
            MemoryKind.PREFERENCE.value,
            MemoryKind.PROJECT_STATE.value,
            MemoryKind.DECISION.value,
        }
    ):
        return MemoryLifecycleState.ACTIVE
    return MemoryLifecycleState.CANDIDATE


def _normalize_kind(
    *,
    explicit_kind: Optional[str] = None,
    message_type: Optional[Any] = None,
    source_kind: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> MemoryKind:
    from ..message_classifier import MessageType  # noqa: PLC0415

    metadata = metadata or {}
    hinted = (
        explicit_kind
        or metadata.get("memory_type")
        or metadata.get("record_type")
        or metadata.get("kind")
    )
    if hinted:
        try:
            return MemoryKind(str(hinted))
        except ValueError:
            pass

    if message_type == MessageType.PREFERENCE:
        return MemoryKind.PREFERENCE
    if message_type == MessageType.TASK_RESULT:
        return MemoryKind.TASK_SIGNAL
    if message_type == MessageType.SYSTEM:
        return MemoryKind.PROJECT_STATE
    if source_kind in {"workflow", "task", "tool_result"}:
        return MemoryKind.TASK_SIGNAL
    if source_kind in {"decision", "routing_decision"} or metadata.get("decision_id"):
        return MemoryKind.DECISION
    if metadata.get("project_id") or metadata.get("workflow_id"):
        return MemoryKind.PROJECT_STATE
    if metadata.get("relationship") or metadata.get("related_memory_ids"):
        return MemoryKind.RELATIONSHIP
    return MemoryKind.FACT


def _sensitivity_from_flags(
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> MemorySensitivity:
    metadata = metadata or {}
    if metadata.get("sensitivity") in {s.value for s in MemorySensitivity}:
        return MemorySensitivity(str(metadata["sensitivity"]))
    if metadata.get("is_sensitive") is True:
        return MemorySensitivity.HIGH
    if is_sensitive_content(text):
        return MemorySensitivity.HIGH
    return MemorySensitivity.LOW


def _normalize_scope(metadata: Dict[str, Any], source_kind: str) -> str:
    scope = metadata.get("scope")
    if scope:
        return str(scope)
    if metadata.get("project_id") or metadata.get("workflow_id"):
        return "project"
    if metadata.get("conversation_id") or metadata.get("source_conversation"):
        return "conversation"
    if metadata.get("tool_name") or metadata.get("tool") or source_kind in {"tool", "tool_result"}:
        return "tool"
    return "global"
