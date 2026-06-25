"""Pure derivation helpers for the memory contract."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, Optional

DEFAULT_SCOPE = "global"
DEFAULT_SENSITIVITY = "low"
DEFAULT_MEMORY_STATE = "active"
RECENCY_DECAY = 0.012
VALID_MEMORY_SCOPES = {"global", "user", "project", "conversation", "tool"}
_TERMINAL_MEMORY_STATES = {"archived", "deleted"}


def _as_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(getattr(value, "value", value))


def _collapse_whitespace(text: str) -> str:
    return " ".join((text or "").split()).strip()


def derive_scope(metadata: Dict[str, Any], source_kind: Optional[str] = None) -> str:
    scope = _as_str(metadata.get("scope"))
    if scope:
        if scope not in VALID_MEMORY_SCOPES:
            raise ValueError(f"invalid memory scope: {scope}")
        return scope
    if metadata.get("project_id") or metadata.get("workflow_id"):
        return "project"
    if metadata.get("conversation_id") or metadata.get("source_conversation"):
        return "conversation"
    if (
        metadata.get("tool_name")
        or metadata.get("tool")
        or metadata.get("source_kind")
        in {
            "tool",
            "tool_result",
        }
    ):
        return "tool"
    if source_kind == "user":
        return "user"
    return DEFAULT_SCOPE


def derive_summary(content: str, metadata: Dict[str, Any]) -> str:
    summary = metadata.get("summary") or metadata.get("short_summary")
    if summary:
        return _collapse_whitespace(_as_str(summary) or "")
    collapsed = _collapse_whitespace(content)
    if len(collapsed) <= 160:
        return collapsed
    return f"{collapsed[:157].rstrip()}..."


def derive_source_ref(
    metadata: Dict[str, Any],
    source_kind: Optional[str],
    source_id: Optional[str],
) -> Dict[str, Any]:
    source_ref: Dict[str, Any] = {}
    conversation_id = (
        metadata.get("conversation_id")
        or metadata.get("source_conversation")
        or metadata.get("conversation")
    )
    message_id = metadata.get("message_id")
    tool_name = metadata.get("tool_name") or metadata.get("tool")

    if source_kind in {"summary", "conversation"} and not conversation_id and source_id:
        conversation_id = source_id
    if (
        source_kind in {"message", "user_message", "assistant_message"}
        and not message_id
        and source_id
    ):
        message_id = source_id

    if conversation_id:
        source_ref["conversation_id"] = _as_str(conversation_id)
    if message_id:
        source_ref["message_id"] = _as_str(message_id)
    if tool_name:
        source_ref["tool_name"] = _as_str(tool_name)
    if not source_ref and source_id:
        source_ref["source_id"] = _as_str(source_id)
    return source_ref


def derive_state(
    *,
    explicit_state: Optional[str],
    is_archived: bool,
    expires_at: Optional[datetime],
    metadata: Dict[str, Any],
) -> str:
    state = _as_str(explicit_state or metadata.get("state") or metadata.get("memory_state"))
    if state:
        return state
    if metadata.get("deleted_at") or metadata.get("deleted") or metadata.get("tombstone"):
        return "deleted"
    if is_archived or (expires_at and expires_at < datetime.now(timezone.utc)):
        return "archived"
    return DEFAULT_MEMORY_STATE


def derive_recency_score(
    created_at: Optional[datetime],
    last_accessed_at: Optional[datetime],
) -> float:
    source = last_accessed_at or created_at
    if source is None:
        return 0.5
    if source.tzinfo is None:
        source = source.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (datetime.now(timezone.utc) - source).total_seconds() / 86400.0)
    return max(0.0, min(1.0, math.exp(-RECENCY_DECAY * age_days)))
