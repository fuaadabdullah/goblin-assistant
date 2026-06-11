"""Memory Re-ranker — scores retrieved memories by usefulness, not just similarity.

Sits between retrieval_service.retrieve_context() and context formatting.
Re-orders the top-K results so that stable, recent, high-value memories
rise above ephemeral noise even when their raw cosine scores are lower.

Scoring formula:
    usefulness = 0.50 * similarity_score
               + 0.25 * recency_factor
               + 0.25 * source_type_weight

All inputs come from the retrieved items themselves — no DB reads, no async,
negligible latency (< 1 ms for k ≤ 20).
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()

# Higher = prefer this source type over raw cosine score.
# memory_facts (stable, deliberately stored) outrank ephemeral recent messages.
_SOURCE_TYPE_WEIGHT: Dict[str, float] = {
    "memory": 1.0,
    "summary": 0.9,
    "document": 0.85,
    "code": 0.85,
    "research": 0.85,
    "task": 0.7,
    "message": 0.5,
    "ephemeral": 0.2,
}
_DEFAULT_TYPE_WEIGHT = 0.5

# Weights for each scoring dimension — must sum to 1.0
_W_SEMANTIC = 0.50
_W_RECENCY = 0.25
_W_TYPE = 0.25

# Recency half-life: ~60 days. 1.0 at creation, ~0.5 at 60 days, ~0.1 at 180 days.
_RECENCY_DECAY = 0.012


def _recency_factor(created_at: Any) -> float:
    """Exponential decay on item age. Returns 0.5 when created_at is unknown."""
    if created_at is None:
        return 0.5
    try:
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_days = max(0.0, (now - created_at).total_seconds() / 86400)
        return math.exp(-_RECENCY_DECAY * age_days)
    except Exception:
        return 0.5


class MemoryReranker:
    """Re-scores retrieved memory items by usefulness and returns them sorted."""

    def rerank(
        self,
        items: List[Dict[str, Any]],
        *,
        query: str,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Re-order items by composite usefulness score.

        Args:
            items: Retrieved memory items from retrieval_service.retrieve_context().
                   Each item must have at minimum a ``score`` (cosine similarity).
            query: The original query string — kept as a parameter so the call
                   site is future-proof for cross-encoder expansion.
            top_k: If provided, return only the top-k results after re-ranking.

        Returns:
            Items sorted by ``rerank_score`` descending, with the score added
            to each item dict.
        """
        if not items:
            return items

        scored: List[Dict[str, Any]] = []
        for item in items:
            rerank_score = self._score(item)
            scored.append({**item, "rerank_score": rerank_score})

        scored.sort(key=lambda x: x["rerank_score"], reverse=True)

        logger.debug(
            "memory_reranker_applied",
            total=len(scored),
            top_source_type=scored[0].get("source_type") if scored else None,
            top_rerank_score=round(scored[0]["rerank_score"], 3) if scored else None,
        )

        return scored[:top_k] if top_k is not None else scored

    def _score(self, item: Dict[str, Any]) -> float:
        similarity = max(0.0, min(1.0, float(item.get("score", 0.5))))
        recency = _recency_factor(item.get("created_at"))
        type_weight = _SOURCE_TYPE_WEIGHT.get(item.get("source_type", ""), _DEFAULT_TYPE_WEIGHT)
        return _W_SEMANTIC * similarity + _W_RECENCY * recency + _W_TYPE * type_weight


memory_reranker = MemoryReranker()
