from __future__ import annotations

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
    record_request_observation(
        method="GET",
        route="/api/v1/chat/conversations",
        status_code=200,
        latency_s=0.125,
        request_id="req-123",
        user_id="user-123",
    )

    metrics = get_prometheus_metrics_text()

    assert "goblin_http_requests_total" in metrics
    assert 'route="/api/v1/chat/conversations"' in metrics
