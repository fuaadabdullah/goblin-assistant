"""
Datadog metrics collector for Goblin Assistant.
Handles observability, tracing, and performance monitoring.
"""

import time
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
import hashlib


@dataclass
class MetricPoint:
    """A single metric data point."""

    name: str
    value: float
    tags: Dict[str, str]
    timestamp: float


class MetricsCollector:
    """Collects and reports metrics to Datadog."""

    def __init__(self, api_key: Optional[str] = None, app_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DD_API_KEY")
        self.app_key = app_key or os.getenv("DD_APP_KEY")
        self.site = os.getenv("DD_SITE", "datadoghq.com")

        # In-memory storage for development (replace with actual Datadog client)
        self.metrics_buffer: list[MetricPoint] = []
        self.max_buffer_size = 1000

        # Metric names
        self.metric_names = {
            "index_upserts": "goblin.index.upserts",
            "index_size": "goblin.index.size",
            "rag_latency": "goblin.rag.latency_ms",
            "rag_hit_rate": "goblin.rag.hit_rate",
            "assistant_requests": "goblin.assistant.request.count",
            "assistant_latency": "goblin.assistant.latency_ms",
            "assistant_tokens": "goblin.assistant.tokens",
            "fallback_count": "goblin.assistant.fallback.count",
            "workflow_runs": "goblin.workflow.run",
            "workflow_accepted": "goblin.workflow.accepted",
        }

    def _hash_user_id(self, user_id: str) -> str:
        """Hash user ID for privacy."""
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]

    def _send_metric(self, name: str, value: float, tags: Dict[str, str]):
        """Send metric to Datadog."""
        point = MetricPoint(name=name, value=value, tags=tags, timestamp=time.time())

        # Buffer metrics for batch sending
        self.metrics_buffer.append(point)

        # Flush if buffer is full
        if len(self.metrics_buffer) >= self.max_buffer_size:
            self._flush_metrics()

    def _flush_metrics(self):
        """Flush buffered metrics to Datadog."""
        if not self.metrics_buffer:
            return

        # In production, send to Datadog API
        # For now, just log to console
        for point in self.metrics_buffer:
            print(f"[METRIC] {point.name}={point.value} {point.tags}")

        self.metrics_buffer.clear()

    async def record_index_upsert(self, repo: str, file_count: int, chunk_count: int):
        """Record index upsert metrics."""
        tags = {"repo": repo, "hashed_repo": self._hash_user_id(repo)}

        self._send_metric(self.metric_names["index_upserts"], file_count, tags)
        self._send_metric(self.metric_names["index_size"], chunk_count, tags)

    async def record_rag_request(
        self, user_id: str, latency_ms: float, hit_rate: float, tokens_used: int
    ):
        """Record RAG request metrics."""
        tags = {
            "user_type": "premium" if user_id != "anonymous" else "free",
            "hashed_user": self._hash_user_id(user_id),
        }

        self._send_metric(self.metric_names["rag_latency"], latency_ms, tags)
        self._send_metric(self.metric_names["rag_hit_rate"], hit_rate, tags)
        self._send_metric(self.metric_names["assistant_tokens"], tokens_used, tags)

    async def record_assistant_request(
        self, user_id: str, provider: str, latency_ms: float, tokens_used: int
    ):
        """Record assistant request metrics."""
        tags = {
            "provider": provider,
            "user_type": "premium" if user_id != "anonymous" else "free",
            "hashed_user": self._hash_user_id(user_id),
        }

        self._send_metric(self.metric_names["assistant_requests"], 1, tags)
        self._send_metric(self.metric_names["assistant_latency"], latency_ms, tags)
        self._send_metric(self.metric_names["assistant_tokens"], tokens_used, tags)

    async def record_fallback(self, user_id: str, from_provider: str, to_provider: str):
        """Record provider fallback metrics."""
        tags = {
            "from_provider": from_provider,
            "to_provider": to_provider,
            "hashed_user": self._hash_user_id(user_id),
        }

        self._send_metric(self.metric_names["fallback_count"], 1, tags)

    async def record_workflow_run(
        self, user_id: str, action: str, latency_ms: float, accepted: bool
    ):
        """Record workflow execution metrics."""
        tags = {
            "action": action,
            "accepted": str(accepted).lower(),
            "hashed_user": self._hash_user_id(user_id),
        }

        self._send_metric(self.metric_names["workflow_runs"], 1, tags)
        if accepted:
            self._send_metric(self.metric_names["workflow_accepted"], 1, tags)

    async def record_error(self, user_id: str, error_type: str, endpoint: str):
        """Record error metrics."""
        tags = {
            "error_type": error_type,
            "endpoint": endpoint,
            "hashed_user": self._hash_user_id(user_id),
        }

        # Use a generic error metric
        self._send_metric("goblin.errors.count", 1, tags)

    async def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary for debugging."""
        return {
            "buffered_metrics": len(self.metrics_buffer),
            "metric_names": self.metric_names,
            "datadog_configured": bool(self.api_key and self.app_key),
        }

    def start_trace(
        self, name: str, tags: Optional[Dict[str, str]] = None
    ) -> "TraceContext":
        """Start a trace (placeholder for actual tracing)."""
        return TraceContext(name, tags or {})

    def flush(self):
        """Flush all buffered metrics."""
        self._flush_metrics()


class TraceContext:
    """Context manager for tracing."""

    def __init__(self, name: str, tags: Dict[str, str]):
        self.name = name
        self.tags = tags
        self.start_time = time.time()

    def __enter__(self):
        print(f"[TRACE START] {self.name} {self.tags}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (time.time() - self.start_time) * 1000
        status = "error" if exc_type else "success"
        print(f"[TRACE END] {self.name} duration={duration:.2f}ms status={status}")

    def set_tag(self, key: str, value: str):
        """Set a trace tag."""
        self.tags[key] = value
