"""Unified memory core for high-signal long-term memory.

This module centralizes memory ingestion, redaction, salience scoring,
relationship metadata, compaction, and privacy-safe export/delete flows.
It builds on the existing ``memory_facts`` and ``embeddings`` tables rather
than introducing a parallel memory backend.
"""

from ._service import MemoryCoreService, memory_core_service
from .classification import (
    _derive_memory_state,
    _merge_memory_state,
    _normalize_scope,
)
from .models import (
    EntityType,
    MemoryKind,
    MemoryLifecycleState,
    MemoryLink,
    MemoryRecord,
    MemorySensitivity,
    RelationType,
)

# Re-export private helpers for backward compatibility with tests
from .scoring import (
    _compute_memory_confidence,
    _compute_memory_importance,
    _compute_salience,
    _derive_explicitness_score,
)

__all__ = [
    "MemoryKind",
    "MemorySensitivity",
    "MemoryLifecycleState",
    "EntityType",
    "RelationType",
    "MemoryLink",
    "MemoryRecord",
    "MemoryCoreService",
    "memory_core_service",
    # Private but re-exported for tests
    "_compute_salience",
    "_compute_memory_confidence",
    "_compute_memory_importance",
    "_derive_explicitness_score",
    "_normalize_scope",
    "_derive_memory_state",
    "_merge_memory_state",
]
