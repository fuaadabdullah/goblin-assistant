from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from fastapi.exceptions import RequestValidationError

from .contracts import ApiErrorPayload
from .error_types import ErrorType


@dataclass
class DomainError(Exception):
    code: str
    message: str
    status_code: int = status.HTTP_400_BAD_REQUEST
    details: Optional[Dict[str, Any]] = None


def _group_validation_errors_by_field(
    errors: list[dict],
) -> Dict[str, list[str]]:
    """Group Pydantic validation errors by field name.

    Args:
        errors: List of Pydantic validation error dicts

    Returns:
        Dict mapping field names to lists of error messages
    """
    grouped: Dict[str, list[str]] = {}
    for error in errors:
        # Get field name from location tuple
        field = ".".join(str(loc) for loc in error.get("loc", []))
        if not field:
            field = "unknown"
        # Get error message
        msg = error.get("msg", "Validation failed")
        if field not in grouped:
            grouped[field] = []
        grouped[field].append(msg)
    return grouped


def map_http_exception(
    exc: HTTPException,
    request_id: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> ApiErrorPayload:
    """Map HTTPException to standardized error payload.

    Args:
        exc: The HTTPException to map
        request_id: Optional request identifier
        timestamp: Optional ISO 8601 timestamp

    Returns:
        StandardizedApiErrorPayload
    """
    detail = exc.detail
    error_type = ErrorType.INTERNAL

    if isinstance(detail, dict):
        code = str(detail.get("code") or "HTTP_ERROR")
        message = str(detail.get("message") or detail.get("detail") or "Request failed")
        details = {k: v for k, v in detail.items() if k not in ("code", "message", "detail")}
        # Ensure details is a dict, or None if empty
        if not details:
            details = None

        # Infer error type from code or category
        if "AUTHENTICATION" in code or "AUTH" in code:
            error_type = ErrorType.AUTHENTICATION
        elif "CHAT_" in code or "PROVIDER" in code:
            error_type = ErrorType.PROVIDER
        elif "VALIDATION" in code or "INPUT" in code:
            error_type = ErrorType.VALIDATION

        return ApiErrorPayload(
            code=code,
            type=error_type,
            message=message,
            request_id=request_id,
            timestamp=timestamp,
            details=details,
        )
    if isinstance(detail, str):
        return ApiErrorPayload(
            code="HTTP_ERROR",
            type=ErrorType.INTERNAL,
            message=detail,
            request_id=request_id,
            timestamp=timestamp,
        )
    return ApiErrorPayload(
        code="HTTP_ERROR",
        type=ErrorType.INTERNAL,
        message="Request failed",
        request_id=request_id,
        timestamp=timestamp,
    )


def map_validation_exception(
    exc: RequestValidationError,
    request_id: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> ApiErrorPayload:
    """Map RequestValidationError to standardized error payload.

    Args:
        exc: The RequestValidationError to map
        request_id: Optional request identifier
        timestamp: Optional ISO 8601 timestamp

    Returns:
        StandardizedApiErrorPayload
    """
    grouped_errors = _group_validation_errors_by_field(exc.errors())
    return ApiErrorPayload(
        code="VALIDATION_ERROR",
        type=ErrorType.VALIDATION,
        message="Request validation failed",
        request_id=request_id,
        timestamp=timestamp,
        details={"errors": grouped_errors},
    )


def map_domain_error(
    exc: DomainError,
    request_id: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> ApiErrorPayload:
    """Map DomainError to standardized error payload.

    Args:
        exc: The DomainError to map
        request_id: Optional request identifier
        timestamp: Optional ISO 8601 timestamp

    Returns:
        StandardizedApiErrorPayload
    """
    return ApiErrorPayload(
        code=exc.code,
        type=ErrorType.BUSINESS_LOGIC,
        message=exc.message,
        request_id=request_id,
        timestamp=timestamp,
        details=exc.details,
    )


def map_unhandled_exception(
    exc: Exception,
    request_id: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> ApiErrorPayload:
    """Map unhandled exception to standardized error payload.

    Args:
        exc: The Exception to map
        request_id: Optional request identifier
        timestamp: Optional ISO 8601 timestamp

    Returns:
        StandardizedApiErrorPayload
    """
    if isinstance(exc, TimeoutError):
        return ApiErrorPayload(
            code="SANDBOX_TIMEOUT",
            type=ErrorType.INTERNAL,
            message="Execution exceeded limit",
            request_id=request_id,
            timestamp=timestamp,
        )
    return ApiErrorPayload(
        code="INTERNAL_ERROR",
        type=ErrorType.INTERNAL,
        message="An internal server error occurred",
        request_id=request_id,
        timestamp=timestamp,
    )
