"""In-memory RoutingRegistry: stats tracking, audit trail, and persistence."""

from __future__ import annotations

import atexit
import collections
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog

from .router_store import ProviderStats, RoutingRegistryStore
from .router_supabase import restore_from_supabase, schedule_mirror

logger = structlog.get_logger()


class RoutingRegistry:
    _AUDIT_MAX = 1000

    def __init__(self, store: Optional[RoutingRegistryStore] = None) -> None:
        self._store = store or RoutingRegistryStore()
        self._stats: Dict[str, ProviderStats] = self._store.load()
        self._hourly_spend: Dict[str, Dict[str, float]] = self._store.load_hourly_spend()
        self._decision_log: collections.deque = collections.deque(maxlen=self._AUDIT_MAX)
        self._dirty = False
        self._dirty_since_at = 0.0
        self._last_mutation_at = 0.0
        self._flush_interval_seconds = self._load_flush_interval()
        atexit.register(self.close)

    def _load_flush_interval(self) -> float:
        raw = os.getenv("ROUTING_REGISTRY_FLUSH_INTERVAL_SECONDS", "5").strip()
        try:
            return max(0.0, float(raw))
        except (TypeError, ValueError):
            return 5.0

    @staticmethod
    def _current_hour_bucket(moment: Optional[float] = None) -> str:
        ts = moment if moment is not None else time.time()
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y%m%d%H")

    def _mark_dirty(self) -> None:
        if not self._dirty:
            self._dirty_since_at = time.time()
        self._dirty = True
        self._last_mutation_at = time.time()

    def _flush_if_due(self) -> None:
        if not self._dirty:
            return
        if self._flush_interval_seconds <= 0:
            self.flush()
            return
        if (
            self._dirty_since_at
            and (time.time() - self._dirty_since_at) >= self._flush_interval_seconds
        ):
            self.flush()

    # ------------------------------------------------------------------
    # Stats access
    # ------------------------------------------------------------------

    def get(self, provider_id: str) -> ProviderStats:
        if provider_id not in self._stats:
            self._stats[provider_id] = ProviderStats(provider_id=provider_id)
        return self._stats[provider_id]

    def record_success(
        self,
        provider_id: str,
        latency_ms: float,
        cost_usd: float = 0.0,
        *,
        request_id: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
    ) -> None:
        stats = self.get(provider_id)
        stats.success_count += 1
        stats.update_latency(latency_ms)
        stats.total_cost_usd += cost_usd
        now = time.time()
        stats.last_used = now
        bucket = self._hourly_spend.setdefault(self._current_hour_bucket(now), {})
        bucket[provider_id] = bucket.get(provider_id, 0.0) + float(cost_usd)
        if request_id is not None:
            self._decision_log.append(
                {
                    "event": "outcome",
                    "request_id": request_id,
                    "provider_id": provider_id,
                    "actual_latency_ms": round(latency_ms, 2),
                    "actual_cost_usd": round(cost_usd, 8),
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "timestamp": now,
                }
            )
        self._mark_dirty()
        self._flush_if_due()

    def record_failure(self, provider_id: str) -> None:
        stats = self.get(provider_id)
        stats.failure_count += 1
        stats.last_used = time.time()
        self._mark_dirty()
        self._flush_if_due()

    def log_decision(
        self,
        *,
        request_id: str,
        cost_weight: float,
        candidates: List[str],
        score_breakdown: Dict[str, Dict[str, float]],
        rank_order: List[str],
    ) -> None:
        self._decision_log.append(
            {
                "event": "decision",
                "request_id": request_id,
                "cost_weight": cost_weight,
                "candidates": candidates,
                "score_breakdown": score_breakdown,
                "rank_order": rank_order,
                "timestamp": time.time(),
            }
        )

    # ------------------------------------------------------------------
    # Snapshots / introspection
    # ------------------------------------------------------------------

    def get_audit_trail(self, limit: int = 200) -> List[Dict[str, Any]]:
        return list(self._decision_log)[-limit:]

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        return {
            pid: {
                "ewma_latency_ms": round(s.ewma_latency_ms, 1),
                "success_rate": round(s.success_rate, 3),
                "total_cost_usd": round(s.total_cost_usd, 6),
                "last_used": s.last_used,
            }
            for pid, s in self._stats.items()
        }

    def current_hour_spend(self) -> Dict[str, float]:
        return dict(self._hourly_spend.get(self._current_hour_bucket(), {}))

    def current_hour_spend_total(self) -> float:
        return round(sum(self.current_hour_spend().values()), 6)

    def hourly_spend_snapshot(self) -> Dict[str, Dict[str, float]]:
        return {
            hb: {pid: round(spend, 6) for pid, spend in provider_spend.items()}
            for hb, provider_spend in self._hourly_spend.items()
        }

    def persisted_snapshot(self) -> Dict[str, Any]:
        return {
            "stats": {
                pid: {
                    "ewma_latency_ms": round(s.ewma_latency_ms, 1),
                    "success_rate": round(s.success_rate, 3),
                    "total_cost_usd": round(s.total_cost_usd, 6),
                    "last_used": s.last_used,
                }
                for pid, s in self._store.load().items()
            },
            "hourly_spend": self._store.load_hourly_spend(),
        }

    def metrics_snapshot(self) -> Dict[str, Any]:
        return {
            "providers": self.snapshot(),
            "current_hour_bucket": self._current_hour_bucket(),
            "current_hour_spend": {
                pid: round(spend, 6) for pid, spend in self.current_hour_spend().items()
            },
            "current_hour_spend_total": self.current_hour_spend_total(),
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def flush(self) -> None:
        self._store.flush(self._stats, self._hourly_spend)
        if not self._store.last_error:
            self._dirty = False
            self._dirty_since_at = 0.0
        schedule_mirror(self._stats, self._hourly_spend)

    async def async_restore_from_supabase(self) -> None:
        await restore_from_supabase(self._stats, self._hourly_spend)

    def close(self) -> None:
        self.flush()

    def persistence_status(self) -> Dict[str, Any]:
        return {
            "path": str(self._store.path),
            "last_loaded_at": self._store.last_loaded_at,
            "last_flushed_at": self._store.last_flushed_at,
            "last_error": self._store.last_error,
            "dirty": self._dirty,
            "dirty_since_at": self._dirty_since_at,
            "last_mutation_at": self._last_mutation_at,
            "flush_interval_seconds": self._flush_interval_seconds,
            "current_hour_bucket": self._current_hour_bucket(),
            "current_hour_spend_total": self.current_hour_spend_total(),
        }


registry = RoutingRegistry()
