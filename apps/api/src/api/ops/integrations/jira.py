"""Jira incoming-webhook publisher for provider operations incidents."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx

from api.core.contracts import ProviderHealthUpdatedPayload

SERVICE_NAME = "goblin-assistant"
HEALTH_EVENT_TYPE = "provider.health.updated"
CIRCUIT_EVENT_TYPE = "provider.circuit_breaker.opened"
FAILING_HEALTH_STATUSES = {"degraded", "unhealthy", "billing_issue"}
FAILING_CIRCUIT_STATES = {"soft_open", "hard_open"}


def jira_provider_ops_enabled() -> bool:
    return bool(
        os.getenv("JIRA_PROVIDER_OPS_WEBHOOK_URL", "").strip()
        and os.getenv("JIRA_PROVIDER_OPS_PROJECT_KEY", "").strip()
    )


def jira_incident_dedupe_key(
    event_type: str,
    provider_id: str,
    state: str,
    *,
    environment: Optional[str] = None,
) -> str:
    env_name = (environment or _environment_name()).strip() or "development"
    return f"{env_name}:{event_type}:{provider_id}:{state}"


def build_provider_health_incident_payload(
    payload: ProviderHealthUpdatedPayload,
    *,
    occurred_at: str,
) -> Dict[str, Any]:
    status = str(payload.status).strip().lower()
    environment = _environment_name()
    return {
        "event_type": HEALTH_EVENT_TYPE,
        "provider_id": payload.provider_id,
        "status": status,
        "circuit_state": "",
        "healthy": payload.healthy,
        "configured": payload.configured,
        "avg_latency_ms": payload.avg_latency_ms,
        "consecutive_failures": payload.consecutive_failures,
        "last_error": payload.last_error,
        "occurred_at": occurred_at,
        "environment": environment,
        "service": SERVICE_NAME,
        "project_key": os.getenv("JIRA_PROVIDER_OPS_PROJECT_KEY", "").strip(),
        "dedupe_key": jira_incident_dedupe_key(
            HEALTH_EVENT_TYPE,
            payload.provider_id,
            status,
            environment=environment,
        ),
        "ops_url": _ops_url("/admin/providers/state"),
    }


def build_circuit_breaker_incident_payload(
    *,
    provider_id: str,
    circuit_state: str,
    error: Optional[str],
    occurred_at: str,
) -> Dict[str, Any]:
    normalized_state = str(circuit_state).strip().lower()
    environment = _environment_name()
    return {
        "event_type": CIRCUIT_EVENT_TYPE,
        "provider_id": provider_id,
        "status": "",
        "circuit_state": normalized_state,
        "healthy": False,
        "configured": True,
        "avg_latency_ms": 0.0,
        "consecutive_failures": 0,
        "last_error": error,
        "occurred_at": occurred_at,
        "environment": environment,
        "service": SERVICE_NAME,
        "project_key": os.getenv("JIRA_PROVIDER_OPS_PROJECT_KEY", "").strip(),
        "dedupe_key": jira_incident_dedupe_key(
            CIRCUIT_EVENT_TYPE,
            provider_id,
            normalized_state,
            environment=environment,
        ),
        "ops_url": _ops_url("/ops/circuit-breakers"),
    }


async def post_jira_provider_ops_payload(payload: Dict[str, Any]) -> bool:
    webhook_url = os.getenv("JIRA_PROVIDER_OPS_WEBHOOK_URL", "").strip()
    project_key = os.getenv("JIRA_PROVIDER_OPS_PROJECT_KEY", "").strip()
    if not webhook_url or not project_key:
        return False

    headers = {"Content-Type": "application/json"}
    webhook_secret = os.getenv("JIRA_PROVIDER_OPS_WEBHOOK_SECRET", "").strip()
    if webhook_secret:
        headers["X-Automation-Webhook-Token"] = webhook_secret

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook_url,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
        return True
    except Exception:
        return False


async def publish_provider_health_incident(
    payload: ProviderHealthUpdatedPayload,
    *,
    occurred_at: str,
) -> bool:
    status = str(payload.status).strip().lower()
    if not jira_provider_ops_enabled():
        return False
    if not payload.configured or status not in FAILING_HEALTH_STATUSES:
        return False
    return await post_jira_provider_ops_payload(
        build_provider_health_incident_payload(payload, occurred_at=occurred_at)
    )


async def publish_circuit_breaker_incident(
    *,
    provider_id: str,
    circuit_state: str,
    error: Optional[str],
    occurred_at: str,
) -> bool:
    normalized_state = str(circuit_state).strip().lower()
    if not jira_provider_ops_enabled():
        return False
    if normalized_state not in FAILING_CIRCUIT_STATES:
        return False
    return await post_jira_provider_ops_payload(
        build_circuit_breaker_incident_payload(
            provider_id=provider_id,
            circuit_state=normalized_state,
            error=error,
            occurred_at=occurred_at,
        )
    )


def _environment_name() -> str:
    return (
        os.getenv("JIRA_ENVIRONMENT", "").strip()
        or os.getenv("ENVIRONMENT", "").strip()
        or "development"
    )


def _ops_url(path: str) -> str:
    base_url = (
        os.getenv("GOBLIN_BACKEND_URL", "").strip()
        or os.getenv("BACKEND_URL", "").strip()
        or "http://127.0.0.1:8001"
    ).rstrip("/")
    return f"{base_url}{path}"
