"""
Prometheus metrics for provider dispatch.

Import and use `dispatch_counter`, `dispatch_latency`, and `record_dispatch`
instead of ad-hoc registry calls where you want observable metrics.
"""

from __future__ import annotations

from typing import Optional

from prometheus_client import Counter, Histogram

dispatch_counter = Counter(
    "goblin_provider_dispatch_total",
    "Total provider dispatch attempts",
    ["provider_id", "model", "outcome", "error_category"],
)

dispatch_latency = Histogram(
    "goblin_provider_dispatch_latency_ms",
    "Provider dispatch latency in milliseconds",
    ["provider_id", "model"],
    buckets=[50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000],
)


def record_dispatch(
    *,
    provider_id: str,
    model: str,
    latency_ms: float,
    ok: bool,
    error_category: Optional[str] = None,
) -> None:
    outcome = "success" if ok else "failure"
    category = error_category or ""
    dispatch_counter.labels(
        provider_id=provider_id,
        model=model,
        outcome=outcome,
        error_category=category,
    ).inc()
    if ok:
        dispatch_latency.labels(provider_id=provider_id, model=model).observe(latency_ms)
