"""Tests for standardized API error response format.

Covers:
- Validation errors (grouped by field)
- Authentication errors
- Business logic errors (DomainError)
- Provider errors (chat/LLM)
- Internal errors (unhandled exceptions)
- Request ID and timestamp presence
- Error type classification
"""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError

from api.core.error_types import ErrorType
from api.core.errors import (
    DomainError,
    _group_validation_errors_by_field,
    map_domain_error,
    map_http_exception,
    map_unhandled_exception,
    map_validation_exception,
)

MULTI_FIELD_MESSAGE_ERRORS = 2
PROVIDER_RETRY_AFTER_SECONDS = 5
VALIDATION_STATUS_CODE = 422


# ───────────────────────────────────────────────────────────────────────
# Tests for validation error grouping
# ───────────────────────────────────────────────────────────────────────


class TestValidationErrorGrouping:
    def test_group_validation_errors_single_field(self):
        """Test grouping errors for a single field."""
        errors = [
            {
                "type": "string_pattern",
                "loc": ("message",),
                "msg": "String should match pattern '^[a-z]+'",
                "input": "Invalid123",
            },
        ]
        result = _group_validation_errors_by_field(errors)
        assert "message" in result
        assert len(result["message"]) == 1

    def test_group_validation_errors_multiple_fields(self):
        """Test grouping errors for multiple fields."""
        errors = [
            {
                "type": "string_type",
                "loc": ("message",),
                "msg": "Input should be a valid string",
                "input": 123,
            },
            {
                "type": "string_too_short",
                "loc": ("message",),
                "msg": "String should have at least 1 character",
                "input": "",
            },
            {
                "type": "string_pattern",
                "loc": ("conversation_id",),
                "msg": "String should match pattern '^[a-z0-9-]+$'",
                "input": "INVALID",
            },
        ]
        result = _group_validation_errors_by_field(errors)
        assert "message" in result
        assert len(result["message"]) == MULTI_FIELD_MESSAGE_ERRORS
        assert "conversation_id" in result
        assert len(result["conversation_id"]) == 1

    def test_group_validation_errors_nested_field(self):
        """Test grouping errors for nested fields."""
        errors = [
            {
                "type": "string_type",
                "loc": ("body", "content", "message"),
                "msg": "Input should be a valid string",
                "input": 123,
            },
        ]
        result = _group_validation_errors_by_field(errors)
        assert "body.content.message" in result


# ───────────────────────────────────────────────────────────────────────
# Tests for error mapping functions
# ───────────────────────────────────────────────────────────────────────


class TestMapHttpException:
    def test_map_validation_error(self):
        """Test mapping validation error HTTPException."""
        exc = HTTPException(
            status_code=422,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "field": "value",
            },
        )
        payload = map_http_exception(exc, "req-123", "2026-05-31T12:00:00Z")

        assert payload.code == "VALIDATION_ERROR"
        assert payload.type == ErrorType.VALIDATION
        assert payload.message == "Request validation failed"
        assert payload.request_id == "req-123"
        assert payload.timestamp == "2026-05-31T12:00:00Z"
        assert payload.details == {"field": "value"}

    def test_map_authentication_error(self):
        """Test mapping authentication error HTTPException."""
        exc = HTTPException(
            status_code=401,
            detail={
                "code": "AUTHENTICATION_REQUIRED",
                "message": "Valid API key required",
            },
        )
        payload = map_http_exception(exc, "req-456", "2026-05-31T12:00:00Z")

        assert payload.code == "AUTHENTICATION_REQUIRED"
        assert payload.type == ErrorType.AUTHENTICATION
        assert payload.request_id == "req-456"

    def test_map_provider_error(self):
        """Test mapping provider error HTTPException."""
        exc = HTTPException(
            status_code=429,
            detail={
                "code": "CHAT_RATE_LIMITED",
                "message": "Rate limit exceeded",
                "provider": "openai",
                "retry_after": 5,
            },
        )
        payload = map_http_exception(exc)

        assert payload.code == "CHAT_RATE_LIMITED"
        assert payload.type == ErrorType.PROVIDER
        assert payload.details["provider"] == "openai"
        assert payload.details["retry_after"] == PROVIDER_RETRY_AFTER_SECONDS

    def test_map_string_detail(self):
        """Test mapping HTTPException with string detail."""
        exc = HTTPException(
            status_code=400,
            detail="Bad request",
        )
        payload = map_http_exception(exc)

        assert payload.code == "HTTP_ERROR"
        assert payload.message == "Bad request"
        assert payload.type == ErrorType.INTERNAL

    def test_map_without_metadata(self):
        """Test mapping without request_id and timestamp."""
        exc = HTTPException(
            status_code=404,
            detail={
                "code": "NOT_FOUND",
                "message": "Resource not found",
            },
        )
        payload = map_http_exception(exc)

        assert payload.request_id is None
        assert payload.timestamp is None


class TestMapDomainError:
    def test_map_domain_error_basic(self):
        """Test mapping DomainError."""
        exc = DomainError(
            code="USER_NOT_FOUND",
            message="User not found",
            status_code=404,
        )
        payload = map_domain_error(exc, "req-789", "2026-05-31T12:00:00Z")

        assert payload.code == "USER_NOT_FOUND"
        assert payload.type == ErrorType.BUSINESS_LOGIC
        assert payload.message == "User not found"
        assert payload.request_id == "req-789"
        assert payload.timestamp == "2026-05-31T12:00:00Z"

    def test_map_domain_error_with_details(self):
        """Test mapping DomainError with details."""
        exc = DomainError(
            code="CONVERSATION_NOT_FOUND",
            message="Conversation not found",
            details={"conversation_id": "conv-123"},
        )
        payload = map_domain_error(exc)

        assert payload.details == {"conversation_id": "conv-123"}


class TestMapValidationException:
    def test_map_pydantic_validation_error(self):
        """Test mapping Pydantic RequestValidationError."""

        # Create a Pydantic model validation error
        class TestModel(BaseModel):
            name: str
            age: int

        try:
            TestModel(name=123, age="invalid")
        except ValidationError as e:
            # Convert Pydantic error to RequestValidationError
            rve = RequestValidationError(errors=e.errors())
            payload = map_validation_exception(rve, "req-999", "2026-05-31T12:00:00Z")

            assert payload.code == "VALIDATION_ERROR"
            assert payload.type == ErrorType.VALIDATION
            assert payload.message == "Request validation failed"
            assert "errors" in payload.details
            assert isinstance(payload.details["errors"], dict)
            assert payload.request_id == "req-999"


class TestMapUnhandledException:
    def test_map_timeout_error(self):
        """Test mapping TimeoutError."""
        exc = TimeoutError("Operation timed out")
        payload = map_unhandled_exception(exc)

        assert payload.code == "SANDBOX_TIMEOUT"
        assert payload.type == ErrorType.INTERNAL
        assert payload.message == "Execution exceeded limit"

    def test_map_generic_exception(self):
        """Test mapping generic Exception."""
        exc = ValueError("Something went wrong")
        payload = map_unhandled_exception(exc)

        assert payload.code == "INTERNAL_ERROR"
        assert payload.type == ErrorType.INTERNAL
        assert payload.message == "An internal server error occurred"

    def test_map_with_metadata(self):
        """Test mapping with metadata."""
        exc = RuntimeError("Test error")
        payload = map_unhandled_exception(exc, "req-111", "2026-05-31T12:00:00Z")

        assert payload.request_id == "req-111"
        assert payload.timestamp == "2026-05-31T12:00:00Z"


# ───────────────────────────────────────────────────────────────────────
# Tests for error response format in HTTP responses
# ───────────────────────────────────────────────────────────────────────


class TestErrorResponseFormat:
    """Integration tests for error responses via HTTP."""

    def test_validation_error_response(self, client):
        """Test validation error response format."""
        response = client.post(
            "/api/v1/api/chat",
            json={"message": "", "conversation_id": "test"},
            headers={"x-api-key": "test-local-llm-key"},
        )

        assert response.status_code == VALIDATION_STATUS_CODE
        data = response.json()

        # Verify envelope structure
        assert data["success"] is False
        assert "error" in data

        error = data["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert error["type"] == ErrorType.VALIDATION
        assert error["message"] == "Request validation failed"
        assert "request_id" in error
        assert "timestamp" in error
        assert "errors" in error["details"]

        # Verify request_id is in header and body
        assert "x-request-id" in response.headers
        assert response.headers["x-request-id"] == error["request_id"]

        # Verify timestamp format (ISO 8601)
        datetime.fromisoformat(error["timestamp"].replace("Z", "+00:00"))

    def test_request_id_in_both_header_and_body(self, client):
        """Test request_id appears in both header and error body."""
        response = client.post(
            "/api/v1/api/chat",
            json={"message": ""},
            headers={"x-api-key": "test-local-llm-key"},
        )

        error = response.json()["error"]
        header_request_id = response.headers.get("x-request-id")

        assert error["request_id"] == header_request_id
        assert header_request_id is not None
        assert len(header_request_id) > 0

    def test_timestamp_format_iso8601(self, client):
        """Test timestamp is valid ISO 8601 format."""
        response = client.post(
            "/api/v1/api/chat",
            json={"message": ""},
            headers={"x-api-key": "test-local-llm-key"},
        )

        error = response.json()["error"]
        timestamp = error["timestamp"]

        # Should be parseable as ISO 8601
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            pytest.fail(f"Timestamp not in ISO 8601 format: {timestamp}")


# ───────────────────────────────────────────────────────────────────────
# Tests for error type classification
# ───────────────────────────────────────────────────────────────────────


class TestErrorTypeClassification:
    """Test that errors are properly classified by type."""

    def test_validation_error_type(self):
        """Test validation errors are classified correctly."""
        exc = HTTPException(
            status_code=422,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "Invalid input",
            },
        )
        payload = map_http_exception(exc)
        assert payload.type == ErrorType.VALIDATION

    def test_authentication_error_type(self):
        """Test authentication errors are classified correctly."""
        exc = HTTPException(
            status_code=401,
            detail={
                "code": "AUTHENTICATION_REQUIRED",
                "message": "Auth failed",
            },
        )
        payload = map_http_exception(exc)
        assert payload.type == ErrorType.AUTHENTICATION

    def test_provider_error_type(self):
        """Test provider errors are classified correctly."""
        codes = [
            "CHAT_RATE_LIMITED",
            "CHAT_TIMEOUT",
            "CHAT_PROVIDER_UNAVAILABLE",
        ]
        for code in codes:
            exc = HTTPException(
                status_code=429,
                detail={
                    "code": code,
                    "message": "Provider error",
                },
            )
            payload = map_http_exception(exc)
            assert payload.type == ErrorType.PROVIDER

    def test_business_logic_error_type(self):
        """Test business logic errors are classified correctly."""
        exc = DomainError(
            code="USER_NOT_FOUND",
            message="User not found",
        )
        payload = map_domain_error(exc)
        assert payload.type == ErrorType.BUSINESS_LOGIC

    def test_internal_error_type(self):
        """Test internal errors are classified correctly."""
        exc = RuntimeError("Something broke")
        payload = map_unhandled_exception(exc)
        assert payload.type == ErrorType.INTERNAL
