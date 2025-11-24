import os
import time
from typing import Optional, Dict, Any
from contextlib import contextmanager
from datadog import initialize, statsd
from ddtrace import tracer

# Initialize Datadog statsd client
def init_datadog_statsd():
    """Initialize DogStatsD client for custom metrics."""
    statsd_host = os.getenv("DD_AGENT_HOST", "127.0.0.1")
    statsd_port = int(os.getenv("DD_DOGSTATSD_PORT", "8125"))

    initialize(
        statsd_host=statsd_host,
        statsd_port=statsd_port,
        statsd_namespace="goblin"
    )

# Call initialization
init_datadog_statsd()

class MetricsCollector:
    """Collect and emit custom metrics to Datadog."""

    def __init__(self, service: str = "goblin-api", env: str = None):
        self.service = service
        self.env = env or os.getenv("DD_ENV", "dev")
        self.default_tags = [
            f"env:{self.env}",
            f"service:{self.service}"
        ]

    def _get_tags(self, additional_tags: Optional[Dict[str, str]] = None) -> list:
        """Build tags list from defaults and additional tags."""
        tags = self.default_tags.copy()
        if additional_tags:
            tags.extend([f"{k}:{v}" for k, v in additional_tags.items()])
        return tags

    def increment_counter(self, metric_name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        statsd.increment(metric_name, value=value, tags=self._get_tags(tags))

    def gauge(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        statsd.gauge(metric_name, value=value, tags=self._get_tags(tags))

    def histogram(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a histogram/timing metric."""
        statsd.histogram(metric_name, value=value, tags=self._get_tags(tags))

    def timing(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a timing metric (alias for histogram)."""
        self.histogram(metric_name, value, tags)

    @contextmanager
    def time_operation(self, metric_name: str, tags: Optional[Dict[str, str]] = None):
        """Context manager to time an operation."""
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.histogram(metric_name, duration_ms, tags)

    def record_request(self, route: str, method: str = "GET", status_code: int = 200,
                      duration_ms: Optional[float] = None, tags: Optional[Dict[str, str]] = None):
        """Record API request metrics."""
        # Request count
        request_tags = {"route": route, "method": method, "status": str(status_code)}
        if tags:
            request_tags.update(tags)
        self.increment_counter("request.count", tags=request_tags)

        # Request duration if provided
        if duration_ms is not None:
            self.histogram("request.latency_ms", duration_ms, tags=request_tags)

    def record_llm_call(self, provider: str, model: str, tokens: Optional[int] = None,
                       cost_usd: Optional[float] = None, duration_ms: Optional[float] = None,
                       success: bool = True, tags: Optional[Dict[str, str]] = None):
        """Record LLM provider call metrics."""
        call_tags = {"provider": provider, "model": model}
        if not success:
            call_tags["status"] = "error"
        if tags:
            call_tags.update(tags)

        # Call count
        self.increment_counter("llm.requests", tags=call_tags)

        # Tokens used
        if tokens is not None:
            self.gauge("llm.tokens", tokens, tags=call_tags)

        # Cost estimate
        if cost_usd is not None:
            self.gauge("llm.cost_estimate_usd", cost_usd, tags=call_tags)

        # Latency
        if duration_ms is not None:
            self.histogram("llm.latency_ms", duration_ms, tags=call_tags)

    def record_provider_error(self, provider: str, error_type: str, tags: Optional[Dict[str, str]] = None):
        """Record provider error metrics."""
        error_tags = {"provider": provider, "error_type": error_type}
        if tags:
            error_tags.update(tags)
        self.increment_counter("provider.errors", tags=error_tags)

    def record_queue_depth(self, queue_name: str, depth: int, tags: Optional[Dict[str, str]] = None):
        """Record queue depth metrics."""
        queue_tags = {"queue": queue_name}
        if tags:
            queue_tags.update(tags)
        self.gauge("worker.queue_depth", depth, tags=queue_tags)

    def record_cache_metrics(self, cache_name: str, hits: int, misses: int, tags: Optional[Dict[str, str]] = None):
        """Record cache hit ratio metrics."""
        total = hits + misses
        if total > 0:
            hit_ratio = hits / total
            cache_tags = {"cache": cache_name}
            if tags:
                cache_tags.update(tags)
            self.gauge("cache.hit_ratio", hit_ratio, tags=cache_tags)


# Global metrics collector instance
metrics = MetricsCollector()

def trace_provider_call(provider: str, model: str, tokens: Optional[int] = None,
                       cost_usd: Optional[float] = None, duration_ms: Optional[float] = None,
                       success: bool = True):
    """Convenience function to trace provider calls."""
    metrics.record_llm_call(provider, model, tokens, cost_usd, duration_ms, success)
