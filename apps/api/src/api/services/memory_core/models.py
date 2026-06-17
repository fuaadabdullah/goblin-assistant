"""Domain models and enums for memory management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..memory_contract import build_memory_contract_payload


class MemoryKind(str, Enum):
    FACT = "fact"
    PREFERENCE = "preference"
    DECISION = "decision"
    PROJECT_STATE = "project_state"
    RELATIONSHIP = "relationship"
    TASK_SIGNAL = "task_signal"


class MemorySensitivity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MemoryLifecycleState(str, Enum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    VERIFIED = "verified"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    DELETED = "deleted"


class EntityType(str, Enum):
    USER = "user"
    PROJECT = "project"
    CONVERSATION = "conversation"
    DOCUMENT = "document"
    TASK = "task"
    DECISION = "decision"
    TOOL = "tool"
    PREFERENCE = "preference"
    PERSON = "person"
    COMPANY = "company"


class RelationType(str, Enum):
    BELONGS_TO = "belongs_to"
    REFERS_TO = "refers_to"
    DEPENDS_ON = "depends_on"
    SUPERSEDES = "supersedes"
    CONFLICTS_WITH = "conflicts_with"
    SUPPORTS = "supports"
    CREATED_FROM = "created_from"
    LINKED_TO = "linked_to"


@dataclass(slots=True)
class MemoryLink:
    """Relationship edge between memories or entities."""

    link_type: str
    target: str
    confidence: float = 1.0
    source: Optional[str] = None


@dataclass(slots=True)
class MemoryRecord:
    """Normalized memory payload used by ingestion and retrieval."""

    id: str
    user_id: str
    content: str
    memory_type: MemoryKind
    category: Optional[str]
    source_kind: str
    source_id: Optional[str]
    confidence: float
    salience_score: float
    sensitivity_level: MemorySensitivity
    retention_days: int
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]
    last_accessed_at: Optional[datetime]
    state: MemoryLifecycleState = MemoryLifecycleState.ACTIVE
    confirmation_count: int = 0
    is_archived: bool = False
    embedding_id: Optional[str] = None
    score: Optional[float] = None
    rerank_score: Optional[float] = None
    related_memory_ids: List[str] = field(default_factory=list)
    entity_refs: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    scope: str = "global"
    confidence_band: str = ""
    confidence_reason: str = ""
    importance: float = 0.0
    importance_band: str = ""
    importance_reason: str = ""
    authored: bool = False
    inferred: bool = False
    direct_correction: bool = False
    contradiction: bool = False
    later_contradicted: bool = False
    repetition_count: int = 1
    explicitness_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return build_memory_contract_payload(
            id=self.id,
            user_id=self.user_id,
            content=self.content,
            scope=self.scope,
            memory_type=self.memory_type.value,
            category=self.category,
            source_kind=self.source_kind,
            source_id=self.source_id,
            confidence=self.confidence,
            confidence_band=self.confidence_band,
            confidence_reason=self.confidence_reason,
            importance=self.importance,
            importance_band=self.importance_band,
            importance_reason=self.importance_reason,
            salience_score=self.salience_score,
            sensitivity_level=self.sensitivity_level.value,
            state=self.state.value,
            retention_days=self.retention_days,
            expires_at=self.expires_at,
            last_accessed_at=self.last_accessed_at,
            authored=self.authored,
            inferred=self.inferred,
            direct_correction=self.direct_correction,
            contradiction=self.contradiction,
            later_contradicted=self.later_contradicted,
            repetition_count=self.repetition_count,
            explicitness_score=self.explicitness_score,
            confirmation_count=self.confirmation_count,
            is_archived=self.is_archived,
            related_memory_ids=self.related_memory_ids,
            entity_refs=self.entity_refs,
            metadata=self.metadata,
            created_at=self.created_at,
            updated_at=self.updated_at,
            embedding_id=self.embedding_id,
            source_type="memory",
            score=self.score,
            rerank_score=self.rerank_score,
        )


def _default_retention_days(memory_type: MemoryKind) -> int:
    return {
        MemoryKind.FACT: 365,
        MemoryKind.PREFERENCE: 540,
        MemoryKind.DECISION: 730,
        MemoryKind.PROJECT_STATE: 90,
        MemoryKind.RELATIONSHIP: 180,
        MemoryKind.TASK_SIGNAL: 30,
    }[memory_type]


def _safe_memory_kind(value: Optional[str], fallback: MemoryKind = MemoryKind.FACT) -> MemoryKind:
    if not value:
        return fallback
    try:
        return MemoryKind(str(value))
    except ValueError:
        return fallback


def _safe_sensitivity(value: Optional[str]) -> MemorySensitivity:
    if not value:
        return MemorySensitivity.LOW
    try:
        return MemorySensitivity(str(value))
    except ValueError:
        return MemorySensitivity.LOW


_MEMORY_STATE_RANK: Dict[MemoryLifecycleState, int] = {
    MemoryLifecycleState.CANDIDATE: 0,
    MemoryLifecycleState.ACTIVE: 1,
    MemoryLifecycleState.VERIFIED: 2,
    MemoryLifecycleState.DEPRECATED: 1,
    MemoryLifecycleState.ARCHIVED: -1,
    MemoryLifecycleState.DELETED: -2,
}


def _safe_memory_state(
    value: Optional[str], fallback: MemoryLifecycleState = MemoryLifecycleState.ACTIVE
) -> MemoryLifecycleState:
    if not value:
        return fallback
    try:
        return MemoryLifecycleState(str(value))
    except ValueError:
        return fallback


def _state_rank(state: MemoryLifecycleState) -> int:
    return _MEMORY_STATE_RANK.get(state, 0)
