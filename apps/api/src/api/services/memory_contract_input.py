"""Normalized input layer for the memory contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Tuple

import structlog

from .memory_derivations import (
    _TERMINAL_MEMORY_STATES,
    DEFAULT_SENSITIVITY,
    VALID_MEMORY_SCOPES,
    derive_recency_score,
    derive_scope,
    derive_source_ref,
    derive_state,
    derive_summary,
)

logger = structlog.get_logger(__name__)
_DEPRECATED_FIELD_COUNTS: Dict[str, int] = {}


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


def _clamp_unit_interval(value: Any, default: float = 0.0) -> float:
    if value is None:
        return float(default)
    try:
        score = float(value)
    except (TypeError, ValueError):
        return float(default)
    return max(0.0, min(1.0, score))


def _record_deprecated_fields(
    fields: Iterable[str], *, context: str, item_id: Optional[str]
) -> Tuple[str, ...]:
    unique_fields: List[str] = []
    seen = set()
    for field in fields:
        if not field or field in seen:
            continue
        seen.add(field)
        unique_fields.append(field)

    if not unique_fields:
        return ()

    for field in unique_fields:
        _DEPRECATED_FIELD_COUNTS[field] = _DEPRECATED_FIELD_COUNTS.get(field, 0) + 1

    logger.warning(
        "deprecated_memory_contract_fields_used",
        context=context,
        memory_id=item_id,
        deprecated_fields=unique_fields,
    )
    return tuple(unique_fields)


def get_deprecated_memory_contract_field_counts() -> Dict[str, int]:
    return dict(_DEPRECATED_FIELD_COUNTS)


def reset_deprecated_memory_contract_field_counts() -> None:
    _DEPRECATED_FIELD_COUNTS.clear()


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


@dataclass(frozen=True, slots=True)
class MemoryFactInput:
    """Normalized memory contract data before versioned serialization."""

    id: str
    content: str
    user_id: Optional[str]
    scope: str
    memory_type: str
    category: Optional[str]
    source_kind: str
    source_id: Optional[str]
    confidence: float
    confidence_band: str
    confidence_reason: Optional[str]
    importance: float
    importance_band: str
    importance_reason: Optional[str]
    salience_score: float
    sensitivity: str
    state: str
    status: str
    tags: Tuple[str, ...]
    entities: Tuple[str, ...]
    source_ref: Dict[str, Any]
    summary: str
    embedding_id: Optional[str]
    authored: bool
    inferred: bool
    direct_correction: bool
    contradiction: bool
    later_contradicted: bool
    repetition_count: int
    explicitness_score: float
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    last_accessed_at: Optional[datetime]
    expires_at: Optional[datetime]
    retention_days: int
    confirmation_count: int
    is_archived: bool
    related_memory_ids: Tuple[str, ...]
    entity_refs: Tuple[Any, ...]
    metadata: Dict[str, Any]
    source_type: str
    score: Optional[float]
    rerank_score: Optional[float]
    recency_score: float
    deprecated_fields: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_memory_fact_input(self)

    @classmethod
    def from_legacy_kwargs(
        cls,
        *,
        id: Any,
        content: Any,
        user_id: Optional[Any] = None,
        scope: Optional[Any] = None,
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
        deprecated_fields: Optional[Iterable[str]] = None,
    ) -> "MemoryFactInput":
        metadata = dict(metadata or {})
        deprecated_field_names = _record_deprecated_fields(
            [
                *(list(deprecated_fields or [])),
                "memory_type" if memory_type is not None else "",
                "salience_score" if salience_score is not None else "",
                "sensitivity_level" if sensitivity_level is not None else "",
                "memory_state" if memory_state is not None else "",
            ],
            context="legacy_kwargs",
            item_id=_as_str(id),
        )
        resolved_content = _collapse_whitespace(_as_str(content) or "")
        resolved_created_at = _as_datetime(created_at)
        resolved_updated_at = _as_datetime(updated_at) or resolved_created_at
        resolved_last_accessed_at = _as_datetime(last_accessed_at)
        resolved_expires_at = _as_datetime(expires_at)
        resolved_scope = _as_str(scope or metadata.get("scope")) or derive_scope(
            metadata, source_kind=_as_str(source_kind or source_type)
        )
        resolved_memory_type = (
            _as_str(
                memory_type
                or metadata.get("memory_type")
                or metadata.get("record_type")
                or category
            )
            or "fact"
        )
        resolved_source_kind = _as_str(
            source_kind or metadata.get("source_kind") or source_type or "memory"
        )
        resolved_confidence = _clamp_unit_interval(
            _first_defined(confidence, metadata.get("confidence"), 0.0)
        )
        resolved_importance = _clamp_unit_interval(
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
                sensitivity_level
                or metadata.get("sensitivity_level")
                or metadata.get("sensitivity")
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
        resolved_explicitness_score = _clamp_unit_interval(
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
        resolved_entity_refs = tuple(entity_refs or metadata.get("entity_refs") or [])
        resolved_embedding_id = _as_str(embedding_id or metadata.get("embedding_id"))
        resolved_summary = derive_summary(resolved_content, metadata)
        resolved_tags = _extract_tags(
            metadata, _as_str(category), resolved_memory_type, resolved_source_kind
        )
        resolved_entities = _extract_entities(metadata, resolved_entity_refs)
        resolved_source_ref = derive_source_ref(metadata, resolved_source_kind, _as_str(source_id))
        resolved_state = derive_state(
            explicit_state=state or memory_state,
            is_archived=is_archived or bool(metadata.get("is_archived")),
            expires_at=resolved_expires_at,
            metadata=metadata,
        )
        resolved_recency_score = derive_recency_score(
            resolved_created_at, resolved_last_accessed_at
        )
        resolved_confidence_band = _as_str(
            confidence_band or metadata.get("confidence_band")
        ) or confidence_band_from_score(resolved_confidence)
        resolved_importance_band = _as_str(
            importance_band or metadata.get("importance_band")
        ) or importance_band_from_score(resolved_importance)
        resolved_confidence_reason = _as_str(confidence_reason or metadata.get("confidence_reason"))
        resolved_importance_reason = _as_str(importance_reason or metadata.get("importance_reason"))
        resolved_source_type = _as_str(source_type) or "memory"
        resolved_score = float(score) if score is not None else None
        resolved_rerank_score = float(rerank_score) if rerank_score is not None else None

        return cls(
            id=_as_str(id) or "",
            content=resolved_content,
            user_id=_as_str(user_id),
            scope=resolved_scope,
            memory_type=resolved_memory_type,
            category=_as_str(category) or metadata.get("category"),
            source_kind=resolved_source_kind,
            source_id=_as_str(source_id),
            confidence=resolved_confidence,
            confidence_band=resolved_confidence_band,
            confidence_reason=resolved_confidence_reason,
            importance=resolved_importance,
            importance_band=resolved_importance_band,
            importance_reason=resolved_importance_reason,
            salience_score=resolved_importance,
            sensitivity=resolved_sensitivity,
            state=resolved_state,
            status=resolved_state,
            tags=tuple(resolved_tags),
            entities=tuple(resolved_entities),
            source_ref=resolved_source_ref,
            summary=resolved_summary,
            embedding_id=resolved_embedding_id,
            authored=resolved_authored,
            inferred=resolved_inferred,
            direct_correction=resolved_direct_correction,
            contradiction=resolved_contradiction,
            later_contradicted=resolved_later_contradicted,
            repetition_count=resolved_repetition_count,
            explicitness_score=resolved_explicitness_score,
            created_at=resolved_created_at,
            updated_at=resolved_updated_at,
            last_accessed_at=resolved_last_accessed_at,
            expires_at=resolved_expires_at,
            retention_days=int(
                retention_days
                if retention_days is not None
                else metadata.get("retention_days") or 0
            ),
            confirmation_count=resolved_confirmation_count,
            is_archived=bool(is_archived or resolved_state in _TERMINAL_MEMORY_STATES),
            related_memory_ids=tuple(resolved_related_memory_ids),
            entity_refs=resolved_entity_refs,
            metadata=metadata,
            source_type=resolved_source_type,
            score=resolved_score,
            rerank_score=resolved_rerank_score,
            recency_score=resolved_recency_score,
            deprecated_fields=deprecated_field_names,
        )

    @classmethod
    def from_item(
        cls,
        item: Dict[str, Any],
        *,
        user_id: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> "MemoryFactInput":
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        deprecated_fields = [
            "fact_text" if "fact_text" in item else "",
            "summary_text" if "summary_text" in item else "",
            "memory_type" if "memory_type" in item or "record_type" in metadata else "",
            "salience_score" if "salience_score" in item or "salience_score" in metadata else "",
            "sensitivity_level"
            if "sensitivity_level" in item
            or "sensitivity_level" in metadata
            or "sensitivity" in metadata
            else "",
            "memory_state" if "memory_state" in item or "memory_state" in metadata else "",
        ]
        return cls.from_legacy_kwargs(
            id=_as_str(item.get("id")) or "",
            user_id=user_id or _as_str(item.get("user_id")),
            content=_as_str(
                item.get("content") or item.get("fact_text") or item.get("summary_text") or ""
            ),
            scope=item.get("scope") or metadata.get("scope"),
            memory_type=item.get("memory_type")
            or metadata.get("memory_type")
            or item.get("category"),
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
            retention_days=_first_defined(
                item.get("retention_days"), metadata.get("retention_days")
            ),
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
            direct_correction=_first_defined(
                item.get("direct_correction"), metadata.get("direct_correction")
            ),
            contradiction=_first_defined(item.get("contradiction"), metadata.get("contradiction")),
            later_contradicted=_first_defined(
                item.get("later_contradicted"), metadata.get("later_contradicted")
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
            deprecated_fields=deprecated_fields,
        )

    def to_payload_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "memory_id": self.id,
            "user_id": self.user_id,
            "scope": self.scope,
            "type": self.memory_type,
            "content": self.content,
            "summary": self.summary,
            "source": self.source_kind,
            "source_ref": dict(self.source_ref),
            "confidence": self.confidence,
            "confidence_band": self.confidence_band,
            "confidence_reason": self.confidence_reason,
            "importance": self.importance,
            "importance_band": self.importance_band,
            "importance_reason": self.importance_reason,
            "recency_score": self.recency_score,
            "sensitivity": self.sensitivity,
            "state": self.state,
            "status": self.status,
            "tags": list(self.tags),
            "entities": list(self.entities),
            "embedding_id": self.embedding_id,
            "authored": self.authored,
            "inferred": self.inferred,
            "direct_correction": self.direct_correction,
            "contradiction": self.contradiction,
            "later_contradicted": self.later_contradicted,
            "repetition_count": self.repetition_count,
            "explicitness_score": self.explicitness_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_accessed_at": self.last_accessed_at.isoformat()
            if self.last_accessed_at
            else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "fact_text": self.content,
            "category": self.category,
            "memory_type": self.memory_type,
            "memory_state": self.state,
            "source_kind": self.source_kind,
            "source_id": self.source_id,
            "salience_score": self.salience_score,
            "sensitivity_level": self.sensitivity,
            "retention_days": self.retention_days,
            "confirmation_count": self.confirmation_count,
            "is_archived": self.is_archived,
            "related_memory_ids": list(self.related_memory_ids),
            "entity_refs": list(self.entity_refs),
            "metadata": dict(self.metadata),
            "source_type": self.source_type,
            "score": self.score,
            "rerank_score": self.rerank_score,
            "deprecated_fields": list(self.deprecated_fields),
        }


def _validate_memory_fact_input(value: MemoryFactInput) -> None:
    if not value.id:
        raise ValueError("memory contract requires a non-empty id")
    if not value.content:
        raise ValueError("memory contract requires non-empty content")
    if value.scope not in VALID_MEMORY_SCOPES:
        raise ValueError(f"memory contract requires a valid scope: {value.scope}")
    if not 0.0 <= value.confidence <= 1.0:
        raise ValueError(f"memory contract requires confidence between 0 and 1: {value.confidence}")
    if not 0.0 <= value.importance <= 1.0:
        raise ValueError(f"memory contract requires importance between 0 and 1: {value.importance}")
    if value.confidence_band is None or not value.confidence_band:
        raise ValueError("memory contract requires confidence_band")
    if value.importance_band is None or not value.importance_band:
        raise ValueError("memory contract requires importance_band")


MemoryContractInput = MemoryFactInput
