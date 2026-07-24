"""
Shared helpers for ContextAssemblyService coverage tests.

Targets six areas of the retrieval pipeline:
  1. Token Budgeting
  2. Chunk Truncation
  3. Context Ordering
  4. Source Attribution
  5. Overflow Handling
  6. Retrieval Failures

Every test answers three questions:
  - Did the right context get selected?
  - Did it fit inside the token budget?
  - Did we lose important information?
"""

from unittest.mock import AsyncMock, patch

from api.services.context_assembly_service import (
    ContextAssemblyService,
    ContextBudget,
    ContextLayer,
)
from api.services.context_assembly_service import orchestrator as orch

# ======================================================================
# Helpers
# ======================================================================


def _make_layer(
    name: str,
    tokens: int,
    source_count: int = 0,
    metadata: dict | None = None,
) -> ContextLayer:
    return ContextLayer(
        name=name,
        content=f"content for {name} " * (tokens // 3 + 1),
        tokens=tokens,
        source_count=source_count,
        metadata=metadata or {},
    )


def _make_minimal_service() -> ContextAssemblyService:
    s = ContextAssemblyService.__new__(ContextAssemblyService)
    s._retrieval_service = None
    s._embedding_service = None
    s.response_reserve_tokens = 1024
    s.default_budget = ContextBudget(
        total_tokens=500,
        system_tokens=50,
        long_term_tokens=50,
        working_memory_tokens=100,
        semantic_retrieval_tokens=100,
        ephemeral_tokens=200,
    )
    s.model_context_windows = {}
    return s


def _patch_layer(target_attr: str, return_value=None, side_effect=None):
    """Patch a single layer assembler with an AsyncMock."""
    if side_effect is not None:
        return patch.object(orch, target_attr, AsyncMock(side_effect=side_effect))
    return patch.object(orch, target_attr, AsyncMock(return_value=return_value))


def _snapshot_patch(return_value="snap-default", side_effect=None):
    """Patch context_snapshotter.create_snapshot."""
    if side_effect is not None:
        return patch.object(
            orch.context_snapshotter,
            "create_snapshot",
            AsyncMock(side_effect=side_effect),
        )
    return patch.object(
        orch.context_snapshotter,
        "create_snapshot",
        AsyncMock(return_value=return_value),
    )


# ======================================================================
# 1. TOKEN BUDGETING
# ======================================================================
