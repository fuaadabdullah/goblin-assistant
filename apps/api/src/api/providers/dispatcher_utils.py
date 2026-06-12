"""Utility classes used by the provider dispatcher.

Extracted from dispatcher.py to keep that module focused on provider
registration, configuration, and request dispatch.
"""

from __future__ import annotations

import random
import time
from typing import Any, Dict, Optional


class CircuitBreaker:
    """Simple circuit breaker: opens after `failure_threshold` failures, resets after `timeout` s."""

    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0) -> None:
        self._threshold = failure_threshold
        self._timeout = timeout
        self._failures = 0
        self._opened_at: Optional[float] = None
        self.state = "CLOSED"

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._threshold:
            self._opened_at = time.monotonic()
            self.state = "OPEN"

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None
        self.state = "CLOSED"

    def is_open(self) -> bool:
        if self.state == "OPEN" and self._opened_at is not None:
            if time.monotonic() - self._opened_at >= self._timeout:
                self.state = "HALF_OPEN"
                return False
            return True
        return False


class LoadBalancer:
    """Round-robin or weighted provider selection."""

    def __init__(self, providers: list, strategy: str = "round_robin") -> None:
        self._providers = list(providers)
        self._strategy = strategy
        self._idx = 0

    def select(self) -> Any:
        if not self._providers:
            raise RuntimeError("No providers")
        if self._strategy == "round_robin":
            p = self._providers[self._idx % len(self._providers)]
            self._idx += 1
            return p
        # weighted — healthy providers get 3x weight; simple approximation
        pool = []
        for p in self._providers:
            pool.append(p)
            pool.append(p)
        return random.choice(pool)


class MetricsCollector:
    """Lightweight in-memory metrics collector."""

    def __init__(self) -> None:
        self._latencies: Dict[str, list] = {}
        self._errors: Dict[str, Dict[str, int]] = {}

    def record_latency(self, provider_id: str, latency_ms: float) -> None:
        self._latencies.setdefault(provider_id, []).append(latency_ms)

    def record_error(self, provider_id: str, error_type: str) -> None:
        counts = self._errors.setdefault(provider_id, {})
        counts[error_type] = counts.get(error_type, 0) + 1

    def get_metrics(self, provider_id: str) -> Optional[Dict[str, Any]]:
        lats = self._latencies.get(provider_id)
        if not lats:
            return None
        lats_sorted = sorted(lats)
        n = len(lats_sorted)
        return {
            "avg_latency": sum(lats_sorted) / n,
            "p99_latency": lats_sorted[min(int(n * 0.99), n - 1)],
            "count": n,
        }

    def get_error_counts(self, provider_id: str) -> Dict[str, int]:
        return dict(self._errors.get(provider_id, {}))

    def generate_report(self) -> Dict[str, Any]:
        return {
            "latencies": {pid: self.get_metrics(pid) for pid in self._latencies},
            "errors": {pid: self.get_error_counts(pid) for pid in self._errors},
        }
