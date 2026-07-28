"""
Retrieval Metrics Router
Exposes the five retrieval health questions as GET endpoints under /debug/retrieval-metrics.
"""

from typing import Optional

import structlog
from fastapi import APIRouter, Query

from ..services.retrieval_metrics_service import retrieval_metrics_service

logger = structlog.get_logger()

router = APIRouter(prefix="/debug/retrieval-metrics", tags=["observability", "retrieval-metrics"])


@router.get("/token-accuracy")
async def get_token_budget_accuracy(window_hours: int = Query(24, ge=1, le=168)):
    """Q1: How accurate is the token budget prediction?

    Returns avg_delta (positive = assembly produced more tokens than predicted,
    typically due to unbudgeted format-string headers), p95_abs_delta, and
    pct_within_5pct over the rolling window.
    """
    return await retrieval_metrics_service.get_token_budget_accuracy(window_hours=window_hours)


@router.get("/tier-latency")
async def get_tier_latency_breakdown(window_hours: int = Query(24, ge=1, le=168)):
    """Q2: How long does each retrieval tier take?

    Returns per-tier (long_term, summary, index, messages, recent) avg/p50/p95 latency
    in milliseconds, plus total assembly latency.
    """
    return await retrieval_metrics_service.get_tier_latency_breakdown(window_hours=window_hours)


@router.get("/cache-hit-rate")
async def get_cache_hit_rate():
    """Q3: What is the application-level Redis cache hit rate?

    Reads in-process counters (not Redis server-global keyspace_hits).
    Reset on process restart.
    """
    return await retrieval_metrics_service.get_cache_hit_rate()


@router.get("/failures")
async def get_failure_summary(window_hours: int = Query(24, ge=1, le=168)):
    """Q4: How often does context assembly fail and in what ways?

    Failure types: embedding_unavailable, layer_skipped, truncation_triggered, assembly_error.
    Layer skip detail distinguishes skip_budget_exhausted from skip_no_data.
    """
    return await retrieval_metrics_service.get_failure_summary(window_hours=window_hours)


@router.get("/embedding-dedup")
async def get_embedding_dedup():
    """Q5: How much duplicate embedding work is being prevented?

    Shows duplicates prevented by process-level content hash cache and DB source_id pre-check.
    """
    return await retrieval_metrics_service.get_embedding_dedup_stats()


@router.get("/report")
async def get_full_report(
    window_hours: int = Query(24, ge=1, le=168),
    user_id: Optional[str] = Query(None),
):
    """All five retrieval health questions in a single response."""
    return await retrieval_metrics_service.get_full_report(
        user_id=user_id, window_hours=window_hours
    )
