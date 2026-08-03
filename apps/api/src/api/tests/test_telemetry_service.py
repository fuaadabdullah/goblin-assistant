"""Tests for api.services.telemetry."""

from __future__ import annotations

from api.services import telemetry
from api.services.telemetry import EventType


def test_log_message_safely_redacts_pii():
    result = telemetry.log_message_safely(
        "My email is user@example.com",
        context={"password": "secret"},
    )

    assert result["has_pii"] is True
    # replacement format is <replace_with>_<PII_TYPE>, e.g. "[REDACTED]_EMAIL"
    assert "[REDACTED" in result["preview"] and "EMAIL" in result["preview"]
    assert result["metadata"]["password"] == "[REDACTED]"


def test_log_inference_metrics_masks_metadata(monkeypatch):
    captured = {}

    def fake_info(message, **kwargs):
        captured.update(message=message, **kwargs)

    monkeypatch.setattr(telemetry.logger, "info", fake_info)
    telemetry.log_inference_metrics(
        provider="openai",
        model="gpt-4o-mini",
        latency_ms=123,
        token_count=456,
        cost_usd=0.12,
        status_code=200,
        metadata={"api_key": "secret"},
    )

    assert captured["message"] == "inference_event"
    assert captured["extra"]["data"]["metadata"]["api_key"] == "[REDACTED]"


def test_log_conversation_event_uses_hashed_ids(monkeypatch):
    captured = {}

    def fake_info(message, **kwargs):
        captured.update(message=message, **kwargs)

    monkeypatch.setattr(telemetry.logger, "info", fake_info)
    telemetry.log_conversation_event(
        EventType.CONVERSATION_START,
        user_id="user-123",
        session_id="session-456",
        message_count=2,
        metadata={"token": "abc"},
    )

    data = captured["extra"]["data"]
    assert captured["message"] == "conversation_event"
    assert data["user_hash"] and data["session_hash"]
    assert "user-123" not in str(data)
    assert "session-456" not in str(data)


def test_log_rag_event_logs_without_raw_content(monkeypatch):
    captured = {}

    def fake_info(message, **kwargs):
        captured.update(message=message, **kwargs)

    monkeypatch.setattr(telemetry.logger, "info", fake_info)

    telemetry.log_rag_event(
        EventType.RAG_QUERY,
        user_id="user-123",
        document_count=4,
        query_latency_ms=55,
        success=True,
    )

    data = captured["extra"]["data"]
    assert captured["message"] == "rag_event"
    assert data["document_count"] == 4
    assert "user-123" not in str(data)


def test_log_privacy_event_logs_audit_fields(monkeypatch):
    captured = {}

    def fake_info(message, **kwargs):
        captured.update(message=message, **kwargs)

    monkeypatch.setattr(telemetry.logger, "info", fake_info)

    telemetry.log_privacy_event(
        EventType.DATA_DELETE,
        user_id="user-123",
        action="delete_conversation",
        item_count=3,
        success=True,
    )

    data = captured["extra"]["data"]
    assert captured["message"] == "privacy_event"
    assert data["action"] == "delete_conversation"


def test_log_error_event_routes_by_severity(monkeypatch):
    calls = []
    monkeypatch.setattr(
        telemetry.logger,
        "critical",
        lambda message, **kwargs: calls.append(("critical", message, kwargs)),
    )
    monkeypatch.setattr(
        telemetry.logger,
        "warning",
        lambda message, **kwargs: calls.append(("warning", message, kwargs)),
    )
    monkeypatch.setattr(
        telemetry.logger,
        "error",
        lambda message, **kwargs: calls.append(("error", message, kwargs)),
    )

    telemetry.log_error_event(
        error_type="runtime",
        error_message="Something broke",
        context={"secret": "hide"},
        severity="critical",
    )

    telemetry.log_error_event(
        error_type="runtime",
        error_message="Something broke",
        context={"secret": "hide"},
        severity="warning",
    )

    telemetry.log_error_event(
        error_type="runtime",
        error_message="Something broke",
        context={"secret": "hide"},
        severity="error",
    )

    severities = [level for level, _, _ in calls]
    assert severities == ["critical", "warning", "error"]
    assert all(message == "error_event" for _, message, _ in calls)
    assert all(
        call_kwargs["extra"]["data"]["context"]["secret"] == "[REDACTED]"
        for _, _, call_kwargs in calls
    )


def test_hash_message_id_is_deterministic():
    masked = telemetry.mask_sensitive({"password": "x"})
    assert masked["password"] == "[REDACTED]"
    assert telemetry.hash_message_id("hello") == telemetry.hash_message_id("hello")


def test_event_type_contains_expected_values():
    assert EventType.INFERENCE_REQUEST.value == "inference.request"
    assert EventType.ERROR.value == "error"
