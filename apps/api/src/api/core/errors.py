from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from fastapi.exceptions import RequestValidationError

from .contracts import ApiErrorPayload


@dataclass
class DomainError(Exception):
    code: str
    message: str
    status_code: int = status.HTTP_400_BAD_REQUEST
    details: Optional[Dict[str, Any]] = None


def map_http_exception(exc: HTTPException) -> ApiErrorPayload:
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code") or "HTTP_ERROR")
        message = str(detail.get("message") or detail.get("detail") or "Request failed")
        details = detail.get("details")
        return ApiErrorPayload(
            code=code,
            message=message,
            details=details if isinstance(details, dict) else None,
        )
    if isinstance(detail, str):
        return ApiErrorPayload(code="HTTP_ERROR", message=detail)
    return ApiErrorPayload(code="HTTP_ERROR", message="Request failed")


def map_validation_exception(exc: RequestValidationError) -> ApiErrorPayload:
    return ApiErrorPayload(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details={"errors": exc.errors()},
    )


def map_unhandled_exception(exc: Exception) -> ApiErrorPayload:
    if isinstance(exc, TimeoutError):
        return ApiErrorPayload(code="SANDBOX_TIMEOUT", message="Execution exceeded limit")
    return ApiErrorPayload(code="INTERNAL_ERROR", message="An internal server error occurred")
