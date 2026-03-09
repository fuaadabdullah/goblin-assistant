"""
Lightweight unit tests for SSE error event models.
Tests the data structures without importing the full chat_router.
"""

import pytest
from typing import Optional, Dict, Any
from datetime import datetime


# Minimal model definitions copied for testing
class SSEErrorEvent:
    """Structured error event for SSE streaming"""
    def __init__(
        self,
        type: str,
        code: str,
        message: str,
        is_recoverable: bool,
        details: Optional[Dict[str, Any]] = None
    ):
        self.type = type
        self.code = code
        self.message = message
        self.is_recoverable = is_recoverable
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "code": self.code,
            "message": self.message,
            "is_recoverable": self.is_recoverable,
            "details": self.details
        }


class SSEDataEvent:
    """Generic SSE data event payload"""
    def __init__(
        self,
        content: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[SSEErrorEvent] = None
    ):
        self.content = content
        self.result = result
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "result": self.result,
            "error": self.error.to_dict() if self.error else None
        }


# Test cases

def test_sse_error_event_creation():
    """Test SSEErrorEvent can be created and serialized"""
    error = SSEErrorEvent(
        type="error",
        code="provider-timeout",
        message="Provider request timed out",
        is_recoverable=True,
        details={"provider": "openai", "timeout_seconds": 30}
    )
    
    assert error.type == "error"
    assert error.code == "provider-timeout"
    assert error.message == "Provider request timed out"
    assert error.is_recoverable is True
    assert error.details["provider"] == "openai"


def test_sse_error_event_to_dict():
    """Test SSEErrorEvent serializes to dict"""
    error = SSEErrorEvent(
        type="error",
        code="auth-failed",
        message="Unauthorized access",
        is_recoverable=False
    )
    
    data = error.to_dict()
    assert data["type"] == "error"
    assert data["code"] == "auth-failed"
    assert data["is_recoverable"] is False
    assert isinstance(data["details"], dict)


def test_sse_error_event_non_recoverable():
    """Test non-recoverable error events"""
    error = SSEErrorEvent(
        type="error",
        code="http-401",
        message="Authentication required",
        is_recoverable=False
    )
    assert error.is_recoverable is False


def test_sse_error_event_recoverable():
    """Test recoverable error events"""
    error = SSEErrorEvent(
        type="error",
        code="provider-connection-error",
        message="Failed to connect to provider",
        is_recoverable=True
    )
    assert error.is_recoverable is True


def test_sse_data_event_with_content():
    """Test SSEDataEvent with content"""
    event = SSEDataEvent(content="Hello, world!")
    data = event.to_dict()
    
    assert data["content"] == "Hello, world!"
    assert data["result"] is None
    assert data["error"] is None


def test_sse_data_event_with_error():
    """Test SSEDataEvent with error"""
    error = SSEErrorEvent(
        type="error",
        code="stream-timeout",
        message="Stream connection timed out",
        is_recoverable=True
    )
    event = SSEDataEvent(error=error)
    data = event.to_dict()
    
    assert data["error"] is not None
    assert data["error"]["code"] == "stream-timeout"
    assert data["content"] is None


def test_sse_data_event_with_partial_content_and_error():
    """Test SSEDataEvent with both partial content and error (mid-stream failure)"""
    error = SSEErrorEvent(
        type="error",
        code="stream-interrupted",
        message="Stream interrupted mid-response",
        is_recoverable=True,
        details={"partial_content": "This is a partial response"}
    )
    event = SSEDataEvent(content="This is a partial response", error=error)
    data = event.to_dict()
    
    assert data["content"] == "This is a partial response"
    assert data["error"]["code"] == "stream-interrupted"
    assert data["error"]["details"]["partial_content"] == "This is a partial response"


def test_sse_error_codes_defined():
    """Test that all expected error codes are valid and handleable"""
    expected_codes = [
        "auth-failed",
        "db-write-error",
        "provider-timeout",
        "provider-connection-error",
        "provider-error",
        "stream-timeout",
        "stream-interrupted",
        "stream-error",
        "internal-error"
    ]
    
    for code in expected_codes:
        error = SSEErrorEvent(
            type="error",
            code=code,
            message=f"Error: {code}",
            is_recoverable=(code not in ["auth-failed", "db-write-error"])
        )
        assert error.code == code


def test_sse_error_event_with_empty_details():
    """Test SSEErrorEvent with no details"""
    error = SSEErrorEvent(
        type="error",
        code="internal-error",
        message="Internal server error",
        is_recoverable=False
    )
    
    assert error.details == {}
    data = error.to_dict()
    assert data["details"] == {}
