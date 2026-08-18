from __future__ import annotations

from unittest.mock import patch

from api.observability.telemetry import (
    get_prometheus_metrics_text,
    record_request_observation,
    redact_payload,
)


def test_redact_payload_masks_sensitive_fields():
    payload = {
        "authorization": "Bearer secret",
        "token": "abc",
        "nested": {"client_secret": "xyz"},
        "safe": "value",
    }

    redacted = redact_payload(payload)

    assert redacted["authorization"] == "[REDACTED]"
    assert redacted["token"] == "[REDACTED]"
    assert redacted["nested"]["client_secret"] == "[REDACTED]"
    assert redacted["safe"] == "value"


def test_record_request_observation_emits_prometheus_metrics():
    with patch("api.observability.telemetry.logger.info") as mock_log:
        record_request_observation(
            method="GET",
            route="/api/v1/chat/conversations",
            status_code=200,
            latency_s=0.125,
            request_id="req-123",
            user_id="user-123",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=12,
            completion_tokens=34,
            cost_usd=0.0123,
            fallback_reason="provider_fallback",
            failure_class="none",
            visible_outcome="success",
            context_sources=["context_assembly", "memory"],
            tool_usage={"count": 2, "tool_names": ["search_web", "summarize"]},
            alternatives_considered=["openai", "anthropic"],
            metadata={"authorization": "Bearer secret", "safe": "value"},
        )

    assert mock_log.call_count == 1
    logged = mock_log.call_args.kwargs
    assert logged["provider"] == "openai"
    assert logged["model"] == "gpt-4o-mini"
    assert logged["fallback_reason"] == "provider_fallback"
    assert logged["failure_class"] == "none"
    assert logged["visible_outcome"] == "success"
    assert logged["context_sources"] == ["context_assembly", "memory"]
    assert logged["tool_usage"] == {"count": 2, "tool_names": ["search_web", "summarize"]}
    assert logged["alternatives_considered"] == ["openai", "anthropic"]
    assert logged["metadata"]["authorization"] == "[REDACTED]"
    assert logged["metadata"]["safe"] == "value"

    metrics = get_prometheus_metrics_text()

    assert "goblin_http_requests_total" in metrics
    assert 'route="/api/v1/chat/conversations"' in metrics
