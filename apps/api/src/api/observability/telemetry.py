"""Canonical observability helpers for requests, auth, and LLM usage.

This module keeps the app's telemetry surface in one place:
- structured request logging
- Prometheus metrics
- optional OpenTelemetry bootstrap
- LiteLLM callback persistence hooks

The code is intentionally defensive: missing optional telemetry packages or
exporters never block request handling.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

logger = structlog.get_logger()

try:  # Optional OTel support.
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    _OTEL_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency path
    trace = None
    OTLPSpanExporter = None
    Resource = None
    TracerProvider = None
    BatchSpanProcessor = None
    FastAPIInstrumentor = None
    HTTPXClientInstrumentor = None
    SQLAlchemyInstrumentor = None
    _OTEL_AVAILABLE = False


HTTP_REQUESTS_TOTAL = Counter(
    "goblin_http_requests_total",
    "Total HTTP requests handled by the API",
    ["method", "route", "status_code"],
)
HTTP_REQUEST_DURATION = Histogram(
    "goblin_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route", "status_code"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
)
HTTP_REQUESTS_IN_FLIGHT = Gauge(
    "goblin_http_requests_in_flight",
    "In-flight HTTP requests",
    ["method", "route"],
)

AUTH_EVENTS_TOTAL = Counter(
    "goblin_auth_events_total",
    "Authentication lifecycle events",
    ["event", "method", "success"],
)

AGENT_TASK_EVENTS_TOTAL = Counter(
    "goblin_agent_task_events_total",
    "Agent task lifecycle events",
    ["event", "status"],
)

LLM_CALLBACKS_TOTAL = Counter(
    "goblin_llm_callbacks_total",
    "LiteLLM callback events received",
    ["provider", "model", "status"],
)
LLM_CALLBACK_DURATION = Histogram(
    "goblin_llm_callback_latency_seconds",
    "LiteLLM callback latency in seconds",
    ["provider", "model"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)
LLM_CALLBACK_COST = Counter(
    "goblin_llm_callback_cost_usd_total",
    "Total LLM cost recorded from LiteLLM callbacks",
    ["provider", "model"],
)
LLM_CALLBACK_TOKENS = Counter(
    "goblin_llm_callback_tokens_total",
    "Total LLM tokens recorded from LiteLLM callbacks",
    ["provider", "model", "kind"],
)

ROUTER_COST_GUARD_EVENTS_TOTAL = Counter(
    "goblin_router_cost_guard_events_total",
    "Router cost guard and kill-switch events",
    ["logical_model", "action"],
)


def init_open_telemetry() -> None:
    """Initialize OTel if the runtime has the optional packages installed."""

    if os.getenv("ENABLE_OPENTELEMETRY", "false").lower() not in {"1", "true", "yes", "on"}:
        return
    if not _OTEL_AVAILABLE:
        logger.warning("otel_unavailable", reason="open-telemetry packages not installed")
        return

    try:
        service_name = os.getenv("OTEL_SERVICE_NAME", "goblin-assistant-api")
        service_version = os.getenv("OTEL_SERVICE_VERSION", "unknown")
        provider = TracerProvider(
            resource=Resource.create(
                {
                    "service.name": service_name,
                    "service.version": service_version,
                    "deployment.environment": os.getenv("ENVIRONMENT", "development"),
                }
            )
        )
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").rstrip("/")
        if endpoint:
            exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
            provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        if HTTPXClientInstrumentor is not None:
            HTTPXClientInstrumentor().instrument()
        if SQLAlchemyInstrumentor is not None:
            SQLAlchemyInstrumentor().instrument()

        logger.info(
            "otel_initialized",
            service_name=service_name,
            endpoint=endpoint or None,
            langfuse_enabled=os.getenv("ENABLE_LANGFUSE", "false").lower()
            in {"1", "true", "yes", "on"},
        )
    except Exception as exc:  # pragma: no cover - bootstrap should not fail runtime
        logger.warning("otel_init_failed", error=str(exc))


def instrument_fastapi_app(app: Any) -> None:
    """Attach FastAPI instrumentation when available."""

    if not _OTEL_AVAILABLE or FastAPIInstrumentor is None:
        return
    try:
        FastAPIInstrumentor.instrument_app(app)
    except Exception as exc:  # pragma: no cover - optional instrumentation
        logger.warning("otel_fastapi_instrumentation_failed", error=str(exc))


def _normalize_route(route: Optional[str]) -> str:
    route = (route or "").strip() or "unknown"
    return route[:120]


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return redact_payload(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, str):
        if len(value) > 512:
            return value[:512] + "..."
        return value
    return value


def redact_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive fields from a payload before logging."""

    sensitive_keys = {
        "authorization",
        "api_key",
        "apikey",
        "password",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "client_secret",
        "callback_secret",
        "code",
    }
    redacted: Dict[str, Any] = {}
    for key, value in payload.items():
        lowered = key.lower()
        if lowered in sensitive_keys or lowered.endswith("_secret") or lowered.endswith("_token"):
            redacted[key] = "[REDACTED]"
        else:
            redacted[key] = _redact_value(value)
    return redacted


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_request_observation(
    *,
    method: str,
    route: str,
    status_code: int,
    latency_s: float,
    request_id: str,
    user_id: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    cost_usd: Optional[float] = None,
    fallback_reason: Optional[str] = None,
    failure_class: Optional[str] = None,
    visible_outcome: Optional[str] = None,
    context_sources: Optional[list[str]] = None,
    tool_usage: Optional[Dict[str, Any]] = None,
    alternatives_considered: Optional[list[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    route_name = _normalize_route(route)
    status = str(status_code)
    HTTP_REQUESTS_TOTAL.labels(method=method, route=route_name, status_code=status).inc()
    HTTP_REQUEST_DURATION.labels(method=method, route=route_name, status_code=status).observe(
        max(0.0, latency_s)
    )

    log_payload: Dict[str, Any] = {
        "event_name": "request_completed",
        "request_id": request_id,
        "method": method,
        "route": route_name,
        "status_code": status_code,
        "latency_ms": round(latency_s * 1000.0, 2),
        "user_id": user_id,
        "provider": provider,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost_usd": cost_usd,
        "fallback_reason": fallback_reason,
        "failure_class": failure_class,
        "visible_outcome": visible_outcome,
        "context_sources": context_sources,
        "tool_usage": tool_usage,
        "alternatives_considered": alternatives_considered,
        "timestamp": _iso_now(),
    }
    if metadata:
        log_payload["metadata"] = redact_payload(metadata)

    logger.info("request_completed", **{k: v for k, v in log_payload.items() if v is not None})


def record_request_start(method: str, route: str) -> None:
    HTTP_REQUESTS_IN_FLIGHT.labels(method=method, route=_normalize_route(route)).inc()


def record_request_end(method: str, route: str) -> None:
    try:
        HTTP_REQUESTS_IN_FLIGHT.labels(method=method, route=_normalize_route(route)).dec()
    except Exception:
        pass


def record_auth_event(*, event: str, method: str, success: bool) -> None:
    AUTH_EVENTS_TOTAL.labels(event=event, method=method, success=str(bool(success)).lower()).inc()
    logger.info(
        "auth_event",
        auth_event=event,
        method=method,
        success=success,
        timestamp=_iso_now(),
    )


def record_agent_task_event(*, event: str, status: str) -> None:
    AGENT_TASK_EVENTS_TOTAL.labels(event=event, status=status).inc()
    logger.info("agent_task_event", task_event=event, status=status, timestamp=_iso_now())


def record_llm_callback(
    *,
    provider: str,
    model: str,
    status: str,
    latency_s: float,
    cost_usd: float,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    route: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    LLM_CALLBACKS_TOTAL.labels(provider=provider, model=model, status=status).inc()
    LLM_CALLBACK_DURATION.labels(provider=provider, model=model).observe(max(0.0, latency_s))
    LLM_CALLBACK_COST.labels(provider=provider, model=model).inc(max(0.0, cost_usd))
    LLM_CALLBACK_TOKENS.labels(provider=provider, model=model, kind="prompt").inc(
        max(0, int(prompt_tokens))
    )
    LLM_CALLBACK_TOKENS.labels(provider=provider, model=model, kind="completion").inc(
        max(0, int(completion_tokens))
    )

    log_payload = {
        "event_name": "llm_callback",
        "request_id": request_id,
        "user_id": user_id,
        "provider": provider,
        "model": model,
        "status": status,
        "route": route,
        "latency_ms": round(latency_s * 1000.0, 2),
        "cost_usd": round(cost_usd, 8),
        "prompt_tokens": max(0, int(prompt_tokens)),
        "completion_tokens": max(0, int(completion_tokens)),
        "timestamp": _iso_now(),
    }
    if metadata:
        log_payload["metadata"] = redact_payload(metadata)
    logger.info("llm_callback_recorded", **{k: v for k, v in log_payload.items() if v is not None})


def record_router_cost_guard_event(
    *,
    logical_model: str,
    action: str,
    cap_usd: Optional[float] = None,
    current_spend_usd: Optional[float] = None,
) -> None:
    ROUTER_COST_GUARD_EVENTS_TOTAL.labels(logical_model=logical_model, action=action).inc()
    logger.info(
        "router_cost_guard_event",
        logical_model=logical_model,
        action=action,
        cap_usd=cap_usd,
        current_spend_usd=current_spend_usd,
        timestamp=_iso_now(),
    )


def get_prometheus_metrics_text() -> str:
    return generate_latest().decode("utf-8")


def get_prometheus_content_type() -> str:
    return CONTENT_TYPE_LATEST


@contextmanager
def request_metric_scope(method: str, route: str):
    record_request_start(method, route)
    try:
        yield
    finally:
        record_request_end(method, route)
