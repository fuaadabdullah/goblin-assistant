"""
RetrievalMetricsService — aggregator for the five retrieval health questions:
  Q1. Token budgeting accuracy
  Q2. Retrieval latency (per tier)
  Q3. Cache hit rates
  Q4. Context assembly failures
  Q5. Embedding consistency / deduplication
"""

import statistics
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()

# Failure type constants
FAILURE_EMBEDDING_UNAVAILABLE = "embedding_unavailable"
FAILURE_LAYER_SKIPPED = "layer_skipped"
FAILURE_TRUNCATION_TRIGGERED = "truncation_triggered"


class RetrievalMetricsService:
    """Rolling-window aggregator for retrieval observability metrics.

    All push methods are synchronous (collections.deque.append is thread-safe
    in CPython) so they can be called from async contexts without await.
    Query methods are async to match the FastAPI router pattern.
    """

    _MAX_WINDOW = 1000  # max events per deque

    def __init__(self) -> None:
        self._tier_timing_events: deque = deque(maxlen=self._MAX_WINDOW)
        self._token_accuracy_events: deque = deque(maxlen=self._MAX_WINDOW)
        self._assembly_latency_events: deque = deque(maxlen=self._MAX_WINDOW)
        self._failure_events: deque = deque(maxlen=self._MAX_WINDOW)

    # ------------------------------------------------------------------
    # Push interface — called by instrumented services
    # ------------------------------------------------------------------

    def record_retrieval_timing(self, user_id: str, tier_timings: Dict[str, float]) -> None:
        """Record per-tier retrieval latency (ms) for one retrieve_context call."""
        self._tier_timing_events.append(
            {"user_id": user_id, "ts": datetime.utcnow(), "tier_timings": tier_timings}
        )
        logger.debug("retrieval_timing_recorded", user_id=user_id, tiers=list(tier_timings.keys()))

    def record_token_accuracy(self, user_id: str, predicted: int, actual: int) -> None:
        """Record predicted vs actual token count after context assembly."""
        delta = actual - predicted
        self._token_accuracy_events.append(
            {
                "user_id": user_id,
                "ts": datetime.utcnow(),
                "predicted": predicted,
                "actual": actual,
                "delta": delta,
            }
        )
        logger.debug(
            "token_accuracy_recorded",
            user_id=user_id,
            predicted=predicted,
            actual=actual,
            delta=delta,
        )

    def record_assembly_latency(self, user_id: str, latency_ms: float) -> None:
        """Record total context assembly latency in milliseconds."""
        self._assembly_latency_events.append(
            {"user_id": user_id, "ts": datetime.utcnow(), "latency_ms": latency_ms}
        )
        logger.debug("assembly_latency_recorded", user_id=user_id, latency_ms=latency_ms)

    def record_failure(self, user_id: str, failure_type: str, layer: str, detail: str = "") -> None:
        """Record a context assembly failure event."""
        self._failure_events.append(
            {
                "user_id": user_id,
                "ts": datetime.utcnow(),
                "failure_type": failure_type,
                "layer": layer,
                "detail": detail,
            }
        )
        logger.debug(
            "assembly_failure_recorded",
            user_id=user_id,
            failure_type=failure_type,
            layer=layer,
            detail=detail,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _filter_window(self, events: deque, window_hours: int) -> List[Dict]:
        cutoff = datetime.utcnow() - timedelta(hours=window_hours)
        return [e for e in events if e["ts"] >= cutoff]

    @staticmethod
    def _percentile(sorted_vals: List[float], pct: float) -> float:
        if not sorted_vals:
            return 0.0
        idx = int(len(sorted_vals) * pct / 100)
        idx = min(idx, len(sorted_vals) - 1)
        return sorted_vals[idx]

    # ------------------------------------------------------------------
    # Query interface — answers the 5 questions
    # ------------------------------------------------------------------

    async def get_token_budget_accuracy(self, window_hours: int = 24) -> Dict[str, Any]:
        """Q1: How accurate is the token budget prediction?

        Returns avg_delta, p95_delta, pct_within_5pct, and sample_count.
        A positive delta means assembly produced MORE tokens than predicted
        (typically due to unbudgeted format-string headers).
        """
        events = self._filter_window(self._token_accuracy_events, window_hours)
        if not events:
            return {"sample_count": 0, "window_hours": window_hours}

        deltas = [e["delta"] for e in events]
        predicted_vals = [e["predicted"] for e in events]
        sorted_abs = sorted(abs(d) for d in deltas)

        within_5pct = sum(1 for e in events if abs(e["delta"]) / max(1, e["predicted"]) <= 0.05)

        return {
            "sample_count": len(events),
            "window_hours": window_hours,
            "avg_delta": round(statistics.mean(deltas), 1),
            "median_delta": round(statistics.median(deltas), 1),
            "p95_abs_delta": round(self._percentile(sorted_abs, 95), 1),
            "max_abs_delta": round(max(sorted_abs), 1),
            "avg_predicted_tokens": round(statistics.mean(predicted_vals), 1),
            "pct_within_5pct": round(within_5pct / len(events) * 100, 1),
        }

    async def get_tier_latency_breakdown(self, window_hours: int = 24) -> Dict[str, Any]:
        """Q2: How long does each retrieval tier take?

        Returns per-tier avg/p50/p95 latency in ms and overall assembly latency.
        """
        tier_events = self._filter_window(self._tier_timing_events, window_hours)
        latency_events = self._filter_window(self._assembly_latency_events, window_hours)

        tier_data: Dict[str, List[float]] = {}
        for event in tier_events:
            for tier, ms in event["tier_timings"].items():
                tier_data.setdefault(tier, []).append(ms)

        tiers_out = {}
        for tier, vals in tier_data.items():
            sorted_vals = sorted(vals)
            tiers_out[tier] = {
                "sample_count": len(vals),
                "avg_ms": round(statistics.mean(vals), 2),
                "p50_ms": round(self._percentile(sorted_vals, 50), 2),
                "p95_ms": round(self._percentile(sorted_vals, 95), 2),
                "max_ms": round(max(vals), 2),
            }

        assembly_out: Dict[str, Any] = {"sample_count": 0}
        if latency_events:
            lats = sorted(e["latency_ms"] for e in latency_events)
            assembly_out = {
                "sample_count": len(lats),
                "avg_ms": round(statistics.mean(lats), 2),
                "p50_ms": round(self._percentile(lats, 50), 2),
                "p95_ms": round(self._percentile(lats, 95), 2),
                "max_ms": round(max(lats), 2),
            }

        return {
            "window_hours": window_hours,
            "tiers": tiers_out,
            "assembly_total": assembly_out,
        }

    async def get_cache_hit_rate(self) -> Dict[str, Any]:
        """Q3: What is the application-level cache hit rate?

        Reads directly from the CacheService in-process counters (not Redis
        server-global keyspace_hits, which covers all Redis operations).
        """
        from .cache_service import cache_service

        return cache_service.get_hit_rate()

    async def get_failure_summary(self, window_hours: int = 24) -> Dict[str, Any]:
        """Q4: How often does context assembly fail and in what ways?"""
        events = self._filter_window(self._failure_events, window_hours)
        total_assemblies = len(self._filter_window(self._assembly_latency_events, window_hours))

        by_type: Dict[str, int] = {}
        by_layer: Dict[str, int] = {}
        for e in events:
            by_type[e["failure_type"]] = by_type.get(e["failure_type"], 0) + 1
            by_layer[e["layer"]] = by_layer.get(e["layer"], 0) + 1

        failure_rate = (
            round(len(events) / total_assemblies * 100, 2) if total_assemblies > 0 else 0.0
        )

        return {
            "sample_count": len(events),
            "window_hours": window_hours,
            "failure_rate_pct": failure_rate,
            "total_assemblies_in_window": total_assemblies,
            "by_type": by_type,
            "by_layer": by_layer,
        }

    async def get_embedding_dedup_stats(self) -> Dict[str, Any]:
        """Q5: How much duplicate embedding work is being prevented?"""
        from .embedding_service import embedding_service

        return embedding_service.get_dedup_stats()

    async def get_full_report(
        self, user_id: Optional[str] = None, window_hours: int = 24
    ) -> Dict[str, Any]:
        """Aggregate all 5 questions into a single response."""
        q1, q2, q3, q4, q5 = (
            await self.get_token_budget_accuracy(window_hours),
            await self.get_tier_latency_breakdown(window_hours),
            await self.get_cache_hit_rate(),
            await self.get_failure_summary(window_hours),
            await self.get_embedding_dedup_stats(),
        )
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "window_hours": window_hours,
            "user_id": user_id,
            "token_budget_accuracy": q1,
            "tier_latency": q2,
            "cache_hit_rate": q3,
            "failure_summary": q4,
            "embedding_dedup": q5,
        }


retrieval_metrics_service = RetrievalMetricsService()
