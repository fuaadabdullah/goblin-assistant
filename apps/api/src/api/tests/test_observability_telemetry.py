from __future__ import annotations

from api.observability.telemetry import (
    AUTH_ATTEMPTS_TOTAL,
    AUTH_SUCCESS_TOTAL,
    CHAT_DURATION_SECONDS,
    PROVIDER_REQUESTS_TOTAL,
    RATE_LIMITER_DEGRADED,
    get_prometheus_metrics_text,
    record_auth_event,
    record_chat_completion,
    record_provider_request,
    record_request_observation,
    redact_payload,
    set_rate_limiter_degraded,
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


def _counter_value(counter, **labels) -> float:
    # NOTE: prometheus_client only creates a child time-series after the first
    # .inc() with that label set. Read via _value on the labeled child (which
    # auto-creates at 0.0 without mutating the exported series semantics).
    return counter.labels(**labels)._value.get()


def test_record_auth_event_emits_slo_attempt_and_success_series():
    before_attempts = _counter_value(AUTH_ATTEMPTS_TOTAL, event="login", method="password")
    before_success = _counter_value(AUTH_SUCCESS_TOTAL, event="login", method="password")

    record_auth_event(event="login", method="password", success=True)
    record_auth_event(event="login", method="password", success=False)

    assert (
        _counter_value(AUTH_ATTEMPTS_TOTAL, event="login", method="password") == before_attempts + 2
    )
    assert (
        _counter_value(AUTH_SUCCESS_TOTAL, event="login", method="password") == before_success + 1
    )


def test_record_provider_request_emits_slo_series():
    before_ok = _counter_value(PROVIDER_REQUESTS_TOTAL, provider_id="openai", result="success")
    before_fail = _counter_value(PROVIDER_REQUESTS_TOTAL, provider_id="openai", result="failure")

    record_provider_request(provider_id="openai", ok=True)
    record_provider_request(provider_id="openai", ok=False)

    assert (
        _counter_value(PROVIDER_REQUESTS_TOTAL, provider_id="openai", result="success")
        == before_ok + 1
    )
    assert (
        _counter_value(PROVIDER_REQUESTS_TOTAL, provider_id="openai", result="failure")
        == before_fail + 1
    )


def test_record_chat_completion_observes_latency_histogram():
    before = CHAT_DURATION_SECONDS.labels(provider="openai")._sum.get()

    record_chat_completion(provider="openai", latency_s=1.25)

    after = CHAT_DURATION_SECONDS.labels(provider="openai")._sum.get()
    assert after > before


def test_set_rate_limiter_degraded_flips_gauge():
    set_rate_limiter_degraded(degraded=True)
    assert RATE_LIMITER_DEGRADED._value.get() == 1.0

    set_rate_limiter_degraded(degraded=False)
    assert RATE_LIMITER_DEGRADED._value.get() == 0.0
