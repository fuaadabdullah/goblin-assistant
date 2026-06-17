"""Canonical memory contract helpers.

These helpers normalize memory facts into a backward-compatible superset
shape without requiring a database migration. The payloads produced here are
used by memory ingestion, retrieval, and debug surfaces.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_SCOPE = "global"

_deprecated_field_counts: Dict[str, int] = {}


def get_deprecated_memory_contract_field_counts() -> Dict[str, int]:
    return dict(_deprecated_field_counts)


def reset_deprecated_memory_contract_field_counts() -> None:
    _deprecated_field_counts.clear()


class MemoryContractInput:
    """Normalized, coerced input derived from legacy kwargs."""

    def __init__(
        self,
        *,
        id: str,
        content: str,
        user_id: str,
        summary: str,
        scope: str,
        source_ref: Dict[str, Any],
        recency_score: float,
    ) -> None:
        self.id = id
        self.content = content
        self.user_id = user_id
        self.summary = summary
        self.scope = scope
        self.source_ref = source_ref
        self.recency_score = recency_score

    @classmethod
    def from_legacy_kwargs(
        cls,
        *,
        id: Any,
        content: Any,
        user_id: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
        source_kind: Optional[str] = None,
        source_id: Optional[str] = None,
        authored: bool = False,  # noqa: ARG003
        **_kwargs: Any,
    ) -> "MemoryContractInput":
        meta = metadata or {}
        return cls(
            id=_as_str(id) or "",
            content=_collapse_whitespace(str(content)) if content else "",
            user_id=_as_str(user_id) or "",
            summary=_collapse_whitespace(
                _as_str(meta.get("summary") or meta.get("short_summary")) or ""
            ),
            scope=source_kind or _derive_scope(meta) or DEFAULT_SCOPE,
            source_ref=_derive_source_ref(meta, source_kind, _as_str(source_id)),
            recency_score=0.5,
        )


DEFAULT_SENSITIVITY = "low"
RECENCY_DECAY = 0.012
DEFAULT_MEMORY_STATE = "active"
_TERMINAL_MEMORY_STATES = {"archived", "deleted"}


def _as_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _first_defined(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _as_datetime(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _collapse_whitespace(text: str) -> str:
    return " ".join((text or "").split()).strip()


def _dedupe(values: Iterable[Any]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        if value is None:
            continue
        text = _as_str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _extract_tags(
    metadata: Dict[str, Any],
    category: Optional[str],
    memory_type: Optional[str],
    source: Optional[str],
) -> List[str]:
    tags: List[str] = []
    raw_tags = metadata.get("tags")
    if isinstance(raw_tags, list):
        tags.extend(raw_tags)
    elif isinstance(raw_tags, str) and raw_tags.strip():
        tags.append(raw_tags.strip())
    for value in (category, memory_type, source):
        if value:
            tags.append(value)
    return _dedupe(tags)


def _extract_entities(metadata: Dict[str, Any], entity_refs: Optional[Iterable[Any]]) -> List[str]:
    entities: List[str] = []
    raw_entities = metadata.get("entities")
    if isinstance(raw_entities, list):
        entities.extend(raw_entities)
    elif isinstance(raw_entities, str) and raw_entities.strip():
        entities.append(raw_entities.strip())

    if entity_refs:
        for item in entity_refs:
            if isinstance(item, dict):
                value = item.get("value") or item.get("name") or item.get("id")
                if value:
                    entities.append(value)
            elif item:
                entities.append(item)

    return _dedupe(entities)


def _derive_scope(metadata: Dict[str, Any]) -> str:
    scope = metadata.get("scope")
    if scope:
        return _as_str(scope) or DEFAULT_SCOPE
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
    return DEFAULT_SCOPE


def _derive_summary(content: str, metadata: Dict[str, Any]) -> str:
    summary = metadata.get("summary") or metadata.get("short_summary")
    if summary:
        return _collapse_whitespace(_as_str(summary) or "")
    collapsed = _collapse_whitespace(content)
    if len(collapsed) <= 160:
        return collapsed
    return f"{collapsed[:157].rstrip()}..."


def _derive_source_ref(
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


def _derive_status(is_archived: bool, expires_at: Optional[datetime]) -> str:
    now = datetime.now(timezone.utc)
    if is_archived:
        return "archived"
    if expires_at and expires_at < now:
        return "archived"
    return DEFAULT_MEMORY_STATE


def _derive_state(
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


def _derive_recency_score(
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


def confidence_band_from_score(score: float) -> str:
    """Return the human-readable confidence band for a normalized score."""
    score = max(0.0, min(1.0, float(score)))
    if score >= 0.90:
        return "strong_stable_memory"
    if score >= 0.70:
        return "likely_true_usable"
    if score >= 0.40:
        return "weak_needs_verification"
    return "do_not_use_by_default"


def importance_band_from_score(score: float) -> str:
    """Return a coarse importance band for ranking and lifecycle behavior."""
    score = max(0.0, min(1.0, float(score)))
    if score >= 0.80:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


_DEPRECATED_KWARGS = ("memory_type", "salience_score", "sensitivity_level", "memory_state")


def build_memory_contract_payload(
    *,
    id: str,
    content: str,
    user_id: Optional[str] = None,
    scope: Optional[str] = None,
    memory_type: Optional[Any] = None,
    category: Optional[Any] = None,
    source_kind: Optional[Any] = None,
    source_id: Optional[Any] = None,
    confidence: Optional[Any] = None,
    confidence_band: Optional[str] = None,
    confidence_reason: Optional[str] = None,
    importance: Optional[Any] = None,
    importance_band: Optional[str] = None,
    importance_reason: Optional[str] = None,
    salience_score: Optional[Any] = None,
    sensitivity_level: Optional[Any] = None,
    state: Optional[str] = None,
    memory_state: Optional[str] = None,
    _extra_deprecated: Optional[List[str]] = None,
    retention_days: Optional[Any] = None,
    expires_at: Optional[Any] = None,
    last_accessed_at: Optional[Any] = None,
    confirmation_count: Optional[Any] = None,
    is_archived: bool = False,
    authored: Optional[bool] = None,
    inferred: Optional[bool] = None,
    direct_correction: Optional[bool] = None,
    contradiction: Optional[bool] = None,
    later_contradicted: Optional[bool] = None,
    repetition_count: Optional[Any] = None,
    explicitness_score: Optional[Any] = None,
    related_memory_ids: Optional[Iterable[Any]] = None,
    entity_refs: Optional[Iterable[Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    created_at: Optional[Any] = None,
    updated_at: Optional[Any] = None,
    embedding_id: Optional[Any] = None,
    source_type: Optional[Any] = None,
    score: Optional[Any] = None,
    rerank_score: Optional[Any] = None,
) -> Dict[str, Any]:
    metadata = dict(metadata or {})
    resolved_content = _collapse_whitespace(_as_str(content) or "")
    resolved_created_at = _as_datetime(created_at)
    resolved_updated_at = _as_datetime(updated_at) or resolved_created_at
    resolved_last_accessed_at = _as_datetime(last_accessed_at)
    resolved_expires_at = _as_datetime(expires_at)
    resolved_scope = _as_str(scope or metadata.get("scope")) or _derive_scope(metadata)
    resolved_memory_type = (
        _as_str(
            memory_type or metadata.get("memory_type") or metadata.get("record_type") or category
        )
        or "fact"
    )
    resolved_source_kind = _as_str(
        source_kind or metadata.get("source_kind") or source_type or "memory"
    )
    resolved_confidence = float(_first_defined(confidence, metadata.get("confidence"), 0.0))
    resolved_importance = float(
        _first_defined(
            importance,
            salience_score,
            metadata.get("importance"),
            metadata.get("salience_score"),
            0.0,
        )
    )
    resolved_sensitivity = (
        _as_str(
            sensitivity_level or metadata.get("sensitivity_level") or metadata.get("sensitivity")
        )
        or DEFAULT_SENSITIVITY
    )
    resolved_confirmation_count = int(
        _first_defined(confirmation_count, metadata.get("confirmation_count"), 0)
    )
    resolved_authored = bool(_first_defined(authored, metadata.get("authored"), False))
    resolved_inferred = bool(_first_defined(inferred, metadata.get("inferred"), False))
    resolved_direct_correction = bool(
        _first_defined(direct_correction, metadata.get("direct_correction"), False)
    )
    resolved_contradiction = bool(
        _first_defined(contradiction, metadata.get("contradiction"), False)
    )
    resolved_later_contradicted = bool(
        _first_defined(later_contradicted, metadata.get("later_contradicted"), False)
    )
    resolved_repetition_count = int(
        _first_defined(repetition_count, metadata.get("repetition_count"), 1)
    )
    resolved_explicitness_score = float(
        _first_defined(
            explicitness_score,
            metadata.get("explicitness_score"),
            0.75 if resolved_authored else 0.5,
        )
    )
    resolved_related_memory_ids = _dedupe(
        related_memory_ids
        or metadata.get("related_memory_ids")
        or metadata.get("related_ids")
        or []
    )
    resolved_entity_refs = list(entity_refs or metadata.get("entity_refs") or [])
    resolved_embedding_id = _as_str(embedding_id or metadata.get("embedding_id"))
    resolved_summary = _derive_summary(resolved_content, metadata)
    resolved_tags = _extract_tags(
        metadata, _as_str(category), resolved_memory_type, resolved_source_kind
    )
    resolved_entities = _extract_entities(metadata, resolved_entity_refs)
    resolved_source_ref = _derive_source_ref(metadata, resolved_source_kind, _as_str(source_id))
    resolved_state = _derive_state(
        explicit_state=state or memory_state,
        is_archived=is_archived or bool(metadata.get("is_archived")),
        expires_at=resolved_expires_at,
        metadata=metadata,
    )
    resolved_status = resolved_state
    resolved_recency_score = _derive_recency_score(resolved_created_at, resolved_last_accessed_at)
    resolved_confidence_band = (
        confidence_band
        or metadata.get("confidence_band")
        or confidence_band_from_score(resolved_confidence)
    )
    resolved_importance_band = (
        importance_band
        or metadata.get("importance_band")
        or importance_band_from_score(resolved_importance)
    )

    # Track deprecated field usage.
    deprecated_fields: List[str] = list(_extra_deprecated or [])
    _kwarg_vals = {
        "memory_type": memory_type,
        "salience_score": salience_score,
        "sensitivity_level": sensitivity_level,
        "memory_state": memory_state,
    }
    for _field in _DEPRECATED_KWARGS:
        if _kwarg_vals[_field] is not None:
            deprecated_fields.append(_field)
            _deprecated_field_counts[_field] = _deprecated_field_counts.get(_field, 0) + 1

    payload: Dict[str, Any] = {
        "id": id,
        "memory_id": id,
        "schema_version": "1.0",
        "user_id": user_id,
        "scope": resolved_scope,
        "type": resolved_memory_type,
        "content": resolved_content,
        "summary": resolved_summary,
        "source": resolved_source_kind,
        "source_ref": resolved_source_ref,
        "confidence": resolved_confidence,
        "confidence_band": resolved_confidence_band,
        "confidence_reason": confidence_reason or metadata.get("confidence_reason"),
        "importance": resolved_importance,
        "importance_band": resolved_importance_band,
        "importance_reason": importance_reason or metadata.get("importance_reason"),
        "recency_score": resolved_recency_score,
        "sensitivity": resolved_sensitivity,
        "state": resolved_state,
        "status": resolved_status,
        "tags": resolved_tags,
        "entities": resolved_entities,
        "embedding_id": resolved_embedding_id,
        "authored": resolved_authored,
        "inferred": resolved_inferred,
        "direct_correction": resolved_direct_correction,
        "contradiction": resolved_contradiction,
        "later_contradicted": resolved_later_contradicted,
        "repetition_count": resolved_repetition_count,
        "explicitness_score": resolved_explicitness_score,
        "created_at": resolved_created_at.isoformat() if resolved_created_at else None,
        "updated_at": resolved_updated_at.isoformat() if resolved_updated_at else None,
        "last_accessed_at": (
            resolved_last_accessed_at.isoformat() if resolved_last_accessed_at else None
        ),
        "expires_at": resolved_expires_at.isoformat() if resolved_expires_at else None,
        # Backward-compatible aliases and legacy fields.
        "fact_text": resolved_content,
        "category": _as_str(category) or metadata.get("category"),
        "memory_type": resolved_memory_type,
        "memory_state": resolved_state,
        "source_kind": resolved_source_kind,
        "source_id": _as_str(source_id),
        "salience_score": resolved_importance,
        "sensitivity_level": resolved_sensitivity,
        "retention_days": int(
            retention_days if retention_days is not None else metadata.get("retention_days") or 0
        ),
        "confirmation_count": resolved_confirmation_count,
        "is_archived": bool(is_archived or resolved_state in _TERMINAL_MEMORY_STATES),
        "related_memory_ids": resolved_related_memory_ids,
        "entity_refs": resolved_entity_refs,
        "metadata": metadata,
        "source_type": _as_str(source_type) or "memory",
        "score": float(score) if score is not None else None,
        "rerank_score": float(rerank_score) if rerank_score is not None else None,
        "deprecated_fields": deprecated_fields,
    }
    return payload


def canonicalize_memory_item(
    item: Dict[str, Any],
    *,
    user_id: Optional[str] = None,
    source_type: Optional[str] = None,
) -> Dict[str, Any]:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    extra_deprecated: List[str] = []
    if "fact_text" in item and not item.get("content"):
        extra_deprecated.append("fact_text")
        _deprecated_field_counts["fact_text"] = _deprecated_field_counts.get("fact_text", 0) + 1
    return build_memory_contract_payload(
        _extra_deprecated=extra_deprecated,
        id=_as_str(item.get("id")) or "",
        user_id=user_id or _as_str(item.get("user_id")),
        content=_as_str(
            item.get("content") or item.get("fact_text") or item.get("summary_text") or ""
        ),
        scope=item.get("scope") or metadata.get("scope"),
        memory_type=item.get("memory_type") or metadata.get("memory_type") or item.get("category"),
        category=item.get("category") or metadata.get("category"),
        source_kind=item.get("source_kind")
        or metadata.get("source_kind")
        or source_type
        or item.get("source_type"),
        source_id=item.get("source_id") or metadata.get("source_id"),
        confidence=_first_defined(
            item.get("confidence"), metadata.get("confidence"), item.get("score")
        ),
        confidence_band=item.get("confidence_band") or metadata.get("confidence_band"),
        confidence_reason=item.get("confidence_reason") or metadata.get("confidence_reason"),
        importance=_first_defined(
            item.get("importance"),
            metadata.get("importance"),
            item.get("salience_score"),
            item.get("score"),
        ),
        importance_band=item.get("importance_band") or metadata.get("importance_band"),
        importance_reason=item.get("importance_reason") or metadata.get("importance_reason"),
        salience_score=_first_defined(
            item.get("salience_score"), metadata.get("salience_score"), item.get("score")
        ),
        sensitivity_level=item.get("sensitivity_level") or metadata.get("sensitivity_level"),
        retention_days=_first_defined(item.get("retention_days"), metadata.get("retention_days")),
        expires_at=item.get("expires_at") or metadata.get("expires_at"),
        last_accessed_at=item.get("last_accessed_at") or metadata.get("last_accessed_at"),
        confirmation_count=_first_defined(
            item.get("confirmation_count"), metadata.get("confirmation_count")
        ),
        is_archived=bool(item.get("is_archived") or metadata.get("is_archived")),
        state=item.get("state") or metadata.get("state"),
        memory_state=item.get("memory_state") or metadata.get("memory_state"),
        authored=_first_defined(item.get("authored"), metadata.get("authored")),
        inferred=_first_defined(item.get("inferred"), metadata.get("inferred")),
        direct_correction=(
            _first_defined(item.get("direct_correction"), metadata.get("direct_correction"))
        ),
        contradiction=_first_defined(item.get("contradiction"), metadata.get("contradiction")),
        later_contradicted=(
            _first_defined(item.get("later_contradicted"), metadata.get("later_contradicted"))
        ),
        repetition_count=_first_defined(
            item.get("repetition_count"), metadata.get("repetition_count")
        ),
        explicitness_score=_first_defined(
            item.get("explicitness_score"), metadata.get("explicitness_score")
        ),
        related_memory_ids=item.get("related_memory_ids") or metadata.get("related_memory_ids"),
        entity_refs=item.get("entity_refs") or metadata.get("entity_refs"),
        metadata=metadata,
        created_at=item.get("created_at"),
        updated_at=item.get("updated_at"),
        embedding_id=item.get("embedding_id") or metadata.get("embedding_id"),
        source_type=source_type or item.get("source_type"),
        score=item.get("score"),
        rerank_score=item.get("rerank_score"),
    )
