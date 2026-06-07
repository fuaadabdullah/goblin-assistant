"""SQLite-backed persistence store for routing statistics."""

from __future__ import annotations

import os
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import structlog

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
            logger.warning("routing_registry_load_failed", path=str(self.path), error=str(exc))
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
                    "SELECT hour_bucket, provider_id, spend_usd FROM provider_hourly_spend"
                ).fetchall()
            spend_by_hour: Dict[str, Dict[str, float]] = {}
            for hour_bucket, provider_id, spend_usd in rows:
                spend_by_hour.setdefault(str(hour_bucket), {})[str(provider_id)] = float(spend_usd)
            return spend_by_hour
        except Exception as exc:  # noqa: BLE001
            self.last_error = str(exc)
            logger.warning(
                "routing_registry_spend_load_failed", path=str(self.path), error=str(exc)
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
            logger.warning("routing_registry_flush_failed", path=str(self.path), error=str(exc))

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
