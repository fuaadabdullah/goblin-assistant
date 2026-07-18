"""
Shared retrieval limits for the semantic chat and memory prompt pipeline.

The retrieval surface should stay intentionally small: callers can ask for a
bounded top-k slice, and the prompt builder only ever injects the strongest
memory facts from that slice.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence

PROMPT_RETRIEVAL_MIN = max(1, int(os.getenv("PROMPT_RETRIEVAL_MIN", "10")))
PROMPT_RETRIEVAL_MAX = max(
    PROMPT_RETRIEVAL_MIN,
    int(os.getenv("PROMPT_RETRIEVAL_MAX", "20")),
)


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(default if value is None else value)
    except (TypeError, ValueError):
        return int(default)


def clamp_prompt_retrieval_k(value: Optional[int], default: int = PROMPT_RETRIEVAL_MIN) -> int:
    """Clamp prompt-facing retrieval depth to the supported top-k window."""
    normalized = _coerce_int(value, default)
    return max(PROMPT_RETRIEVAL_MIN, min(normalized, PROMPT_RETRIEVAL_MAX))


def clamp_memory_search_limit(value: Optional[int], default: int = PROMPT_RETRIEVAL_MIN) -> int:
    """Clamp direct memory-search requests without forcing the prompt minimum."""
    normalized = _coerce_int(value, default)
    return max(1, min(normalized, PROMPT_RETRIEVAL_MAX))


def _memory_fact_score(item: Dict[str, Any]) -> float:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    raw_score = item.get("rerank_score")
    if raw_score is None:
        raw_score = item.get("score")
    if raw_score is None and isinstance(metadata, dict):
        raw_score = metadata.get("score")
    try:
        return float(raw_score)
    except (TypeError, ValueError):
        return 0.0


def select_top_memory_facts(
    items: Sequence[Dict[str, Any]],
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Return the strongest memory facts, capped to the supported prompt budget."""
    if not items:
        return []

    capped_limit = PROMPT_RETRIEVAL_MAX if limit is None else clamp_memory_search_limit(limit)
    if capped_limit <= 0:
        return []

    ranked = sorted(items, key=_memory_fact_score, reverse=True)
    return list(ranked[:capped_limit])
