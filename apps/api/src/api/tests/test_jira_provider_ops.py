from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from api.core.contracts import ProviderHealthUpdatedPayload
from api.ops.integrations.jira import (
    build_circuit_breaker_incident_payload,
    build_provider_health_incident_payload,
    jira_incident_dedupe_key,
    publish_provider_health_incident,
)
from api.providers.base import BaseProvider, ProviderHealth, ProviderResult
from api.providers.dispatcher_pkg.execution import _record_provider_failure


class _StubProvider(BaseProvider):
    async def invoke(self, messages=None, model=None, **kwargs):
        _ = messages, kwargs
        return ProviderResult(ok=True, provider=self.provider_id, model=model or "stub")

    async def stream(self, messages=None, model=None, **kwargs):
        _ = messages, model, kwargs
        if False:
            yield {}

    async def health_check(self):
        return ProviderHealth(provider_id=self.provider_id, healthy=True)


def test_jira_incident_dedupe_key_uses_environment_event_provider_and_state() -> None:
    assert (
        jira_incident_dedupe_key(
            "provider.health.updated",
            "openai",
            "billing_issue",
            environment="production",
        )
        == "production:provider.health.updated:openai:billing_issue"
    )


def test_build_provider_health_incident_payload_includes_expected_contract(monkeypatch) -> None:
    monkeypatch.setenv("JIRA_PROVIDER_OPS_PROJECT_KEY", "PROVOPS")
    monkeypatch.setenv("JIRA_ENVIRONMENT", "production")
    monkeypatch.setenv("BACKEND_URL", "https://backend.example.com")

    payload = build_provider_health_incident_payload(
        ProviderHealthUpdatedPayload(
            provider_id="openai",
            status="billing_issue",
            configured=True,
            healthy=False,
            avg_latency_ms=912.4,
            success_rate=0.2,
            consecutive_failures=4,
            last_error="quota exceeded",
        ),
        occurred_at="2026-06-05T12:00:00+00:00",
    )

    assert payload["event_type"] == "provider.health.updated"
    assert payload["provider_id"] == "openai"
    assert payload["status"] == "billing_issue"
    assert payload["project_key"] == "PROVOPS"
    assert payload["dedupe_key"] == "production:provider.health.updated:openai:billing_issue"
    assert payload["ops_url"] == "https://backend.example.com/admin/providers/state"


def test_build_circuit_breaker_incident_payload_includes_expected_contract(monkeypatch) -> None:
    monkeypatch.setenv("JIRA_PROVIDER_OPS_PROJECT_KEY", "PROVOPS")
    monkeypatch.setenv("JIRA_ENVIRONMENT", "staging")
    monkeypatch.setenv("BACKEND_URL", "https://backend.example.com")

    payload = build_circuit_breaker_incident_payload(
        provider_id="anthropic",
        circuit_state="hard_open",
        error="exceeded your current quota",
        occurred_at="2026-06-05T12:00:00+00:00",
    )

    assert payload["event_type"] == "provider.circuit_breaker.opened"
    assert payload["circuit_state"] == "hard_open"
    assert payload["dedupe_key"] == "staging:provider.circuit_breaker.opened:anthropic:hard_open"
    assert payload["ops_url"] == "https://backend.example.com/ops/circuit-breakers"


@pytest.mark.asyncio
async def test_publish_provider_health_incident_noops_when_jira_disabled(monkeypatch) -> None:
    monkeypatch.delenv("JIRA_PROVIDER_OPS_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("JIRA_PROVIDER_OPS_PROJECT_KEY", raising=False)

    payload = ProviderHealthUpdatedPayload(
        provider_id="openai",
        status="unhealthy",
        configured=True,
        healthy=False,
        avg_latency_ms=100.0,
        success_rate=0.1,
        consecutive_failures=3,
        last_error="timeout",
    )

    with patch(
        "api.ops.integrations.jira.post_jira_provider_ops_payload",
        new_callable=AsyncMock,
    ) as post_payload:
        result = await publish_provider_health_incident(
            payload,
            occurred_at="2026-06-05T12:00:00+00:00",
        )

    assert result is False
    post_payload.assert_not_awaited()


@pytest.mark.asyncio
async def test_record_provider_failure_publishes_once_on_soft_open_transition() -> None:
    provider = _StubProvider("stub", {"default_model": "stub-model"})

    with patch(
        "api.providers.dispatcher_pkg.execution.publish_circuit_breaker_incident",
        new_callable=AsyncMock,
        return_value=True,
    ) as publish_incident:
        await _record_provider_failure(
            "stub",
            provider,
            "timeout one",
            category="timeout",
        )
        await _record_provider_failure(
            "stub",
            provider,
            "timeout two",
            category="timeout",
        )
        await _record_provider_failure(
            "stub",
            provider,
            "timeout three",
            category="timeout",
        )

    assert provider.circuit_state == "soft_open"
    publish_incident.assert_awaited_once()
    assert publish_incident.await_args.kwargs["circuit_state"] == "soft_open"


@pytest.mark.asyncio
async def test_record_provider_failure_publishes_hard_open_transition() -> None:
    provider = _StubProvider("stub", {"default_model": "stub-model"})

    with patch(
        "api.providers.dispatcher_pkg.execution.publish_circuit_breaker_incident",
        new_callable=AsyncMock,
        return_value=True,
    ) as publish_incident:
        await _record_provider_failure(
            "stub",
            provider,
            "exceeded your current quota",
            category="rate-limit",
        )

    assert provider.circuit_state == "hard_open"
    publish_incident.assert_awaited_once()
    assert publish_incident.await_args.kwargs["circuit_state"] == "hard_open"
