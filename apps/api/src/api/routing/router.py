"""Routing strategies and runtime statistics for provider selection."""

from __future__ import annotations

import atexit
import asyncio
import collections
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from ..providers.pricing import resolve_model_pricing

logger = structlog.get_logger()


@dataclass
class ProviderStats:
    provider_id: str
    ewma_latency_ms: float = 5000.0
    ewma_alpha: float = 0.2
    success_count: int = 0
    failure_count: int = 0
    total_cost_usd: float = 0.0
    last_used: float = field(default_factory=time.time)

    def update_latency(self, latency_ms: float) -> None:
        self.ewma_latency_ms = (
            self.ewma_alpha * latency_ms + (1 - self.ewma_alpha) * self.ewma_latency_ms
        )

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 1.0


class RoutingRegistryStore:
    def __init__(self, path: Optional[str] = None) -> None:
        configured = path if path is not None else os.getenv("ROUTING_REGISTRY_DB_PATH", "")
        default_path = Path(os.getcwd()) / "routing_registry.db"
        self.path = Path(configured).expanduser() if configured else default_path
        self.enabled = bool(path or configured or not os.getenv("PYTEST_CURRENT_TEST"))
        self.last_loaded_at = 0.0
        self.last_flushed_at = 0.0
        self.last_error = ""

    def load(self) -> Dict[str, ProviderStats]:
        if not self.enabled:
            return {}
        try:
            if not self.path.exists():
                return {}
            with sqlite3.connect(str(self.path)) as conn:
                self._ensure_schema(conn)
                rows = conn.execute(
                    """
                    SELECT provider_id, ewma_latency_ms, ewma_alpha, success_count,
                           failure_count, total_cost_usd, last_used
                    FROM provider_routing_stats
                    """
                ).fetchall()
            self.last_loaded_at = time.time()
            self.last_error = ""
            return {
                str(row[0]): ProviderStats(
                    provider_id=str(row[0]),
                    ewma_latency_ms=float(row[1]),
                    ewma_alpha=float(row[2]),
                    success_count=int(row[3]),
                    failure_count=int(row[4]),
                    total_cost_usd=float(row[5]),
                    last_used=float(row[6]),
                )
                for row in rows
            }
        except Exception as exc:  # noqa: BLE001
            self.last_error = str(exc)
            logger.warning(
                "routing_registry_load_failed",
                path=str(self.path),
                error=str(exc),
            )
            return {}

    def load_hourly_spend(self) -> Dict[str, Dict[str, float]]:
        if not self.enabled:
            return {}
        try:
            if not self.path.exists():
                return {}
            with sqlite3.connect(str(self.path)) as conn:
                self._ensure_schema(conn)
                rows = conn.execute(
                    """
                    SELECT hour_bucket, provider_id, spend_usd
                    FROM provider_hourly_spend
                    """
                ).fetchall()
            spend_by_hour: Dict[str, Dict[str, float]] = {}
            for hour_bucket, provider_id, spend_usd in rows:
                bucket = spend_by_hour.setdefault(str(hour_bucket), {})
                bucket[str(provider_id)] = float(spend_usd)
            return spend_by_hour
        except Exception as exc:  # noqa: BLE001
            self.last_error = str(exc)
            logger.warning(
                "routing_registry_spend_load_failed",
                path=str(self.path),
                error=str(exc),
            )
            return {}

    def flush(
        self,
        stats: Dict[str, ProviderStats],
        hourly_spend: Dict[str, Dict[str, float]],
    ) -> None:
        if not self.enabled:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(str(self.path)) as conn:
                self._ensure_schema(conn)
                now = time.time()
                conn.executemany(
                    """
                    INSERT INTO provider_routing_stats (
                        provider_id, ewma_latency_ms, ewma_alpha, success_count,
                        failure_count, total_cost_usd, last_used, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(provider_id) DO UPDATE SET
                        ewma_latency_ms = excluded.ewma_latency_ms,
                        ewma_alpha = excluded.ewma_alpha,
                        success_count = excluded.success_count,
                        failure_count = excluded.failure_count,
                        total_cost_usd = excluded.total_cost_usd,
                        last_used = excluded.last_used,
                        updated_at = excluded.updated_at
                    """,
                    [
                        (
                            item.provider_id,
                            item.ewma_latency_ms,
                            item.ewma_alpha,
                            item.success_count,
                            item.failure_count,
                            item.total_cost_usd,
                            item.last_used,
                            now,
                        )
                        for item in stats.values()
                    ],
                )
                conn.execute("DELETE FROM provider_hourly_spend")
                conn.executemany(
                    """
                    INSERT INTO provider_hourly_spend (
                        hour_bucket, provider_id, spend_usd, updated_at
                    ) VALUES (?, ?, ?, ?)
                    ON CONFLICT(hour_bucket, provider_id) DO UPDATE SET
                        spend_usd = excluded.spend_usd,
                        updated_at = excluded.updated_at
                    """,
                    [
                        (hour_bucket, provider_id, spend_usd, now)
                        for hour_bucket, provider_spend in hourly_spend.items()
                        for provider_id, spend_usd in provider_spend.items()
                    ],
                )
            self.last_flushed_at = time.time()
            self.last_error = ""
        except Exception as exc:  # noqa: BLE001
            self.last_error = str(exc)
            logger.warning(
                "routing_registry_flush_failed",
                path=str(self.path),
                error=str(exc),
            )

    @staticmethod
    def _ensure_schema(conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS provider_routing_stats (
                provider_id TEXT PRIMARY KEY,
                ewma_latency_ms REAL NOT NULL,
                ewma_alpha REAL NOT NULL,
                success_count INTEGER NOT NULL,
                failure_count INTEGER NOT NULL,
                total_cost_usd REAL NOT NULL,
                last_used REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS provider_hourly_spend (
                hour_bucket TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                spend_usd REAL NOT NULL,
                updated_at REAL NOT NULL,
                PRIMARY KEY (hour_bucket, provider_id)
            )
            """
        )


class RoutingRegistry:
    _AUDIT_MAX = 1000  # ring buffer capacity for decision audit trail

    def __init__(self, store: Optional[RoutingRegistryStore] = None) -> None:
        self._store = store or RoutingRegistryStore()
        self._stats: Dict[str, ProviderStats] = self._store.load()
        self._hourly_spend: Dict[str, Dict[str, float]] = self._store.load_hourly_spend()
        self._decision_log: collections.deque = collections.deque(maxlen=self._AUDIT_MAX)
        self._dirty = False
        self._dirty_since_at = 0.0
        self._last_mutation_at = 0.0
        self._flush_interval_seconds = self._load_flush_interval_seconds()
        atexit.register(self.close)

    def _load_flush_interval_seconds(self) -> float:
        raw_value = os.getenv("ROUTING_REGISTRY_FLUSH_INTERVAL_SECONDS", "5").strip()
        try:
            return max(0.0, float(raw_value))
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
        if self._dirty_since_at and (time.time() - self._dirty_since_at) >= self._flush_interval_seconds:
            self.flush()

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
        hour_bucket = self._current_hour_bucket(now)
        bucket = self._hourly_spend.setdefault(hour_bucket, {})
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
        """Append a routing decision record to the audit trail."""
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

    def get_audit_trail(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Return the most recent decision+outcome records."""
        return list(self._decision_log)[-limit:]

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        return {
            provider_id: {
                "ewma_latency_ms": round(stats.ewma_latency_ms, 1),
                "success_rate": round(stats.success_rate, 3),
                "total_cost_usd": round(stats.total_cost_usd, 6),
                "last_used": stats.last_used,
            }
            for provider_id, stats in self._stats.items()
        }

    def current_hour_spend(self) -> Dict[str, float]:
        return dict(self._hourly_spend.get(self._current_hour_bucket(), {}))

    def current_hour_spend_total(self) -> float:
        return round(sum(self.current_hour_spend().values()), 6)

    def hourly_spend_snapshot(self) -> Dict[str, Dict[str, float]]:
        return {
            hour_bucket: {provider_id: round(spend, 6) for provider_id, spend in provider_spend.items()}
            for hour_bucket, provider_spend in self._hourly_spend.items()
        }

    def persisted_snapshot(self) -> Dict[str, Any]:
        return {
            "stats": {
                provider_id: {
                    "ewma_latency_ms": round(stats.ewma_latency_ms, 1),
                    "success_rate": round(stats.success_rate, 3),
                    "total_cost_usd": round(stats.total_cost_usd, 6),
                    "last_used": stats.last_used,
                }
                for provider_id, stats in self._store.load().items()
            },
            "hourly_spend": self._store.load_hourly_spend(),
        }

    def metrics_snapshot(self) -> Dict[str, Any]:
        return {
            "providers": self.snapshot(),
            "current_hour_bucket": self._current_hour_bucket(),
            "current_hour_spend": {
                provider_id: round(spend, 6)
                for provider_id, spend in self.current_hour_spend().items()
            },
            "current_hour_spend_total": self.current_hour_spend_total(),
        }

    def flush(self) -> None:
        self._store.flush(self._stats, self._hourly_spend)
        if not self._store.last_error:
            self._dirty = False
            self._dirty_since_at = 0.0

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


class LatencyRouter:
    def rank(
        self,
        candidates: List[str],
        provider_costs: Dict[str, tuple[float, float]],
    ) -> List[str]:
        del provider_costs

        def score(provider_id: str) -> float:
            stats = registry.get(provider_id)
            reliability = max(stats.success_rate, 0.01)
            return stats.ewma_latency_ms / reliability

        return sorted(candidates, key=score)


class CostRouter:
    def rank(
        self,
        candidates: List[str],
        provider_costs: Dict[str, tuple[float, float]],
    ) -> List[str]:
        def cost_score(provider_id: str) -> float:
            input_cost, output_cost = provider_costs.get(provider_id, (0.0, 0.0))
            return input_cost + output_cost

        return sorted(candidates, key=cost_score)


class HybridRouter:
    def __init__(self, cost_weight: float = 0.35) -> None:
        self.cost_weight = max(0.0, min(1.0, cost_weight))

    def rank(
        self,
        candidates: List[str],
        provider_costs: Dict[str, tuple[float, float]],
        *,
        request_id: Optional[str] = None,
    ) -> List[str]:
        if not candidates:
            return []

        req_id = request_id or str(uuid.uuid4())

        latencies = {pid: registry.get(pid).ewma_latency_ms for pid in candidates}
        costs = {pid: sum(provider_costs.get(pid, (0.0, 0.0))) for pid in candidates}
        max_latency = max(latencies.values()) or 1.0
        max_cost = max(costs.values()) or 1.0

        breakdown: Dict[str, Dict[str, float]] = {}

        def score(provider_id: str) -> float:
            stats = registry.get(provider_id)
            normalized_latency = latencies[provider_id] / max_latency
            normalized_cost = costs[provider_id] / max_cost if max_cost else 0.0
            reliability = max(stats.success_rate, 0.1)
            final = (
                (1 - self.cost_weight) * normalized_latency + self.cost_weight * normalized_cost
            ) / reliability
            breakdown[provider_id] = {
                "normalized_latency": round(normalized_latency, 4),
                "normalized_cost": round(normalized_cost, 4),
                "reliability": round(reliability, 4),
                "final_score": round(final, 6),
            }
            return final

        ranked = sorted(candidates, key=score)

        # Structured audit log
        logger.info(
            "routing_decision",
            request_id=req_id,
            cost_weight=self.cost_weight,
            candidates=candidates,
            rank_order=ranked,
            score_breakdown=breakdown,
        )
        registry.log_decision(
            request_id=req_id,
            cost_weight=self.cost_weight,
            candidates=candidates,
            score_breakdown=breakdown,
            rank_order=ranked,
        )

        return ranked


class ModelTierRouter:
    TIER_PROVIDERS: Dict[str, List[str]] = {
        "fast": ["groq", "siliconeflow", "gemini"],
        "smart": ["openai", "anthropic", "deepseek", "aliyun"],
        "best": ["openai", "anthropic", "gcp_vllm", "azure_openai"],
        "local": ["gcp_vm", "ollama_local", "aliyun"],
    }

    TIER_MODELS: Dict[str, Dict[str, str]] = {
        "fast": {
            "groq": "llama-3.3-70b-versatile",
            "siliconeflow": "Qwen/Qwen2.5-7B-Instruct",
            "gemini": "gemini-2.0-flash",
        },
        "smart": {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-haiku-latest",
            "deepseek": "deepseek-chat",
            "aliyun": "qwen-plus",
        },
        "best": {
            "openai": "gpt-4o",
            "anthropic": "claude-sonnet-4-20250514",
            "gcp_vllm": "qwen3-32b",
            "azure_openai": "gpt-4o",
        },
        "local": {
            "gcp_vm": "qwen2.5:3b",
            "ollama_local": "qwen2.5:3b",
            "aliyun": "qwen-plus",
        },
    }

    def providers_for_tier(self, tier: str) -> List[str]:
        return list(self.TIER_PROVIDERS.get(tier, self.TIER_PROVIDERS["smart"]))

    def model_for_provider(self, tier: str, provider_id: str) -> Optional[str]:
        return self.TIER_MODELS.get(tier, {}).get(provider_id)


latency_router = LatencyRouter()
cost_router = CostRouter()
hybrid_router = HybridRouter(cost_weight=float(os.getenv("ROUTING_COST_WEIGHT", "0.35")))
tier_router = ModelTierRouter()


def _dispatcher():
    from ..providers.dispatcher import dispatcher

    return dispatcher


def _provider_costs(provider_ids: List[str]) -> Dict[str, tuple[float, float]]:
    dispatch = _dispatcher()
    costs: Dict[str, tuple[float, float]] = {}
    for provider_id in provider_ids:
        provider = dispatch.get_provider(provider_id)
        pricing = resolve_model_pricing(
            provider.provider_id,
            provider.default_model or None,
            config=provider.config,
        )
        costs[provider_id] = (pricing.input_per1k, pricing.output_per1k)
    return costs


def top_providers_for(
    capability: str,
    prefer_local: bool = False,
    prefer_cost: bool = False,
    limit: int = 6,
) -> List[str]:
    dispatch = _dispatcher()
    candidates = dispatch.top_providers_for(
        capability,
        prefer_local=prefer_local,
        prefer_cost=prefer_cost,
        limit=max(1, limit),
    )
    if not candidates:
        return []

    if prefer_cost:
        ranked = cost_router.rank(candidates, _provider_costs(candidates))
        return ranked[: max(1, limit)]

    if prefer_local:
        local_candidates = [
            provider_id
            for provider_id in tier_router.providers_for_tier("local")
            if provider_id in candidates
        ]
        return local_candidates[: max(1, limit)]

    return candidates[: max(1, limit)]


async def route_task(
    task_type: str,
    payload: Dict[str, Any],
    prefer_local: bool = False,
    prefer_cost: bool = False,
    max_retries: int = 2,
    stream: bool = False,
) -> Dict[str, Any]:
    dispatch = _dispatcher()
    candidates = top_providers_for(
        capability=task_type,
        prefer_local=prefer_local,
        prefer_cost=prefer_cost,
        limit=max(1, max_retries + 1),
    )
    if not candidates:
        return {"ok": False, "error": "no providers available", "providers_tried": []}

    last_error = "Routing failed"
    for provider_id in candidates:
        result = await dispatch.invoke_provider(
            provider_id=provider_id,
            model=(payload.get("model") if isinstance(payload.get("model"), str) else None),
            payload=payload,
            timeout_ms=int(payload.get("timeout_ms", 30000)),
            stream=stream,
        )
        if isinstance(result, dict) and result.get("ok"):
            result.setdefault("selected_provider", provider_id)
            return result
        if isinstance(result, dict):
            last_error = str(result.get("error", last_error))

    return {
        "ok": False,
        "error": last_error,
        "providers_tried": candidates,
    }


def route_task_sync(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    try:
        asyncio.get_running_loop()
        return {
            "ok": False,
            "error": "route_task_sync cannot run inside an active event loop",
        }
    except RuntimeError:
        return asyncio.run(route_task(*args, **kwargs))
