"""Memory Re-ranker — scores retrieved memories by usefulness, not just similarity.

Sits between retrieval_service.retrieve_context() and context formatting.
Re-orders the top-K results so that stable, recent, high-value memories
rise above ephemeral noise even when their raw cosine scores are lower.

Scoring formula (weights sum to 1.0):
    score = 0.35 * relevance        (cosine similarity)
          + 0.20 * confidence       (0–1 ingestion confidence)
          + 0.20 * importance       (salience / importance score)
          + 0.10 * recency          (exp decay, ~60-day half-life)
          + 0.10 * frequency        (confirmation_count, normalized to 10)
          + 0.05 * scope_match      (1.0 if memory scope == request scope)

Adjustments applied after base score (then clamped to [0, 1]):
    +0.15  direct_correction
    -0.10  contradiction
    -0.15  later_contradicted
    -0.10  is_duplicate (metadata flag)
    -0.08  is_stale (metadata flag)
    -0.12  is_sensitive and no permission

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
    "fact": 1.0,
    "preference": 1.05,
    "decision": 1.08,
    "project_state": 0.98,
    "relationship": 0.92,
    "task_signal": 0.88,
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

_CONFIDENCE_BAND_RANK = {
    "strong_stable_memory": 3,
    "likely_true_usable": 2,
    "weak_needs_verification": 1,
    "do_not_use_by_default": 0,
}

_STATE_BONUS = {
    "verified": 0.18,
    "active": 0.10,
    "candidate": 0.02,
    "deprecated": -0.20,
    "archived": -0.45,
    "deleted": -1.0,
}


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


_MEMORY_SOURCE_TYPES = frozenset(
    {
        "memory",
        "fact",
        "decision",
        "preference",
        "project_state",
        "relationship",
        "task_signal",
        "summary",
    }
)


def _score_adjustments(
    *,
    direct_correction: bool,
    contradiction: bool,
    later_contradicted: bool,
    is_duplicate: bool,
    is_stale: bool,
    sensitivity: str,
    has_permission: bool,
    source_type: str,
    memory_state: str,
) -> float:
    delta = 0.0
    if direct_correction:
        delta += 0.15
    if contradiction:
        delta -= 0.10
    if later_contradicted:
        delta -= 0.15
    if is_duplicate:
        delta -= 0.10
    if is_stale:
        delta -= 0.08
    if sensitivity in {"high", "medium"} and not has_permission:
        delta -= 0.12
    if source_type in _MEMORY_SOURCE_TYPES:
        delta += _STATE_BONUS.get(memory_state, 0.0)
    return delta


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
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}

        relevance = max(0.0, min(1.0, float(item.get("score", 0.5))))

        confidence = max(
            0.0, min(1.0, float(item.get("confidence", metadata.get("confidence", 0.5))))
        )

        importance = max(
            0.0,
            min(
                1.0,
                float(
                    item.get(
                        "importance",
                        metadata.get(
                            "importance", item.get("salience_score", item.get("score", 0.5))
                        ),
                    )
                ),
            ),
        )

        recency_source = item.get("last_accessed_at") or item.get("created_at")
        recency = _recency_factor(recency_source)

        confirmation_count = int(
            item.get("confirmation_count", metadata.get("confirmation_count", 0))
        )
        frequency = min(confirmation_count, 10) / 10.0

        memory_scope = str(item.get("scope", metadata.get("scope", "global")))
        context_scope = str(metadata.get("_context_scope", "global"))
        scope_match = 1.0 if memory_scope == context_scope else 0.0

        memory_type_key = (
            item.get("type")
            or metadata.get("memory_type")
            or metadata.get("record_type")
            or item.get("source_type", "")
        )
        type_weight = _SOURCE_TYPE_WEIGHT.get(
            str(memory_type_key or item.get("source_type", "")), _DEFAULT_TYPE_WEIGHT
        )

        score = (
            0.35 * relevance
            + 0.20 * confidence
            + 0.20 * importance
            + 0.10 * recency
            + 0.10 * frequency
            + 0.05 * scope_match
            + 0.03 * type_weight  # tiebreaker preserving memory > message > ephemeral ordering
        )

        direct_correction = bool(item.get("direct_correction") or metadata.get("direct_correction"))
        contradiction = bool(item.get("contradiction") or metadata.get("contradiction"))
        later_contradicted = bool(
            item.get("later_contradicted") or metadata.get("later_contradicted")
        )
        is_duplicate = bool(metadata.get("is_duplicate"))
        is_stale = bool(metadata.get("is_stale"))
        sensitivity = str(item.get("sensitivity_level", metadata.get("sensitivity_level", "low")))
        has_permission = bool(metadata.get("allow_sensitive"))
        source_type = str(item.get("source_type", metadata.get("source_type", "")))
        memory_state = str(
            item.get("state")
            or item.get("memory_state")
            or metadata.get("memory_state")
            or metadata.get("state")
            or "active"
        )

        score += _score_adjustments(
            direct_correction=direct_correction,
            contradiction=contradiction,
            later_contradicted=later_contradicted,
            is_duplicate=is_duplicate,
            is_stale=is_stale,
            sensitivity=sensitivity,
            has_permission=has_permission,
            source_type=source_type,
            memory_state=memory_state,
        )
        return max(0.0, min(1.0, score))


memory_reranker = MemoryReranker()
