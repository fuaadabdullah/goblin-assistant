"""Tests for api.services.telemetry."""

from __future__ import annotations

import api.services.telemetry as telemetry
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

    def fake_info(message):
        captured["message"] = message

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

    assert "Inference:" in captured["message"]
    assert "[REDACTED]" in captured["message"]


def test_log_conversation_event_uses_hashed_ids(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        telemetry.logger,
        "info",
        lambda message: captured.setdefault("message", message),
    )
    telemetry.log_conversation_event(
        EventType.CONVERSATION_START,
        user_id="user-123",
        session_id="session-456",
        message_count=2,
        metadata={"token": "abc"},
    )

    assert "Conversation:" in captured["message"]
    assert "user-123" not in captured["message"]
    assert "session-456" not in captured["message"]


def test_log_rag_event_logs_without_raw_content(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        telemetry.logger,
        "info",
        lambda message: captured.setdefault("message", message),
    )

    telemetry.log_rag_event(
        EventType.RAG_QUERY,
        user_id="user-123",
        document_count=4,
        query_latency_ms=55,
        success=True,
    )

    assert "RAG:" in captured["message"]
    assert "user-123" not in captured["message"]


def test_log_privacy_event_logs_audit_fields(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        telemetry.logger,
        "info",
        lambda message: captured.setdefault("message", message),
    )

    telemetry.log_privacy_event(
        EventType.DATA_DELETE,
        user_id="user-123",
        action="delete_conversation",
        item_count=3,
        success=True,
    )

    assert "Privacy:" in captured["message"]
    assert "delete_conversation" in captured["message"]


def test_log_error_event_routes_by_severity(monkeypatch):
    calls = []
    monkeypatch.setattr(
        telemetry.logger,
        "critical",
        lambda message: calls.append(("critical", message)),
    )
    monkeypatch.setattr(
        telemetry.logger,
        "warning",
        lambda message: calls.append(("warning", message)),
    )
    monkeypatch.setattr(
        telemetry.logger,
        "error",
        lambda message: calls.append(("error", message)),
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

    severities = [level for level, _ in calls]
    assert severities == ["critical", "warning", "error"]


def test_hash_message_id_is_deterministic():
    masked = telemetry.mask_sensitive({"password": "x"})
    assert masked["password"] == "[REDACTED]"
    assert telemetry.hash_message_id("hello") == telemetry.hash_message_id(
        "hello"
    )


def test_event_type_contains_expected_values():
    assert EventType.INFERENCE_REQUEST.value == "inference.request"
    assert EventType.ERROR.value == "error"
