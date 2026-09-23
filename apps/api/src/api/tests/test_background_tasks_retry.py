"""Unit tests for the tenacity-backed summarization retry policy."""

from __future__ import annotations

import asyncio

from api.services.background_tasks import (
    _is_retryable_summary_exception,
    _SummaryGenerationError,
)


def test_retries_transient_categories() -> None:
    for category in ("server-error", "rate-limit", "timeout", "connection"):
        assert _is_retryable_summary_exception(_SummaryGenerationError(category, "boom")) is True


def test_does_not_retry_auth_or_client_categories() -> None:
    for category in ("auth", "model-error", "unknown"):
        assert _is_retryable_summary_exception(_SummaryGenerationError(category, "boom")) is False


def test_retries_network_and_timeout_exceptions() -> None:
    assert _is_retryable_summary_exception(ConnectionError("refused")) is True
    assert _is_retryable_summary_exception(TimeoutError("timed out")) is True
    assert _is_retryable_summary_exception(asyncio.TimeoutError()) is True


def test_summary_error_keeps_category() -> None:
    error = _SummaryGenerationError("rate-limit", "quota exceeded")
    assert error.category == "rate-limit"
    assert str(error) == "quota exceeded"
