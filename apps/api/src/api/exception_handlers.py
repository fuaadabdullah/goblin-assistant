import uuid
from datetime import datetime, timezone

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .core.contracts import ErrorEnvelope
from .core.errors import (
    DomainError,
    map_domain_error,
    map_http_exception,
    map_unhandled_exception,
    map_validation_exception,
)
from .core.route_lifecycle import classify_route_lifecycle
from .observability.migration_metrics import migration_metrics

logger = structlog.get_logger()


def _get_request_metadata(request: Request) -> tuple[str, str]:
    """Extract or generate request_id and timestamp from request context.

    Returns:
        Tuple of (request_id, timestamp)
    """
    # Try to get request_id from structlog context (set by middleware)
    request_id = None
    try:
        context = structlog.contextvars.get_contextvars()
        request_id = context.get("request_id")
    except Exception:
        logger.debug("structlog_context_unavailable", exc_info=True)

    # Generate if not found
    if not request_id:
        request_id = str(uuid.uuid4())

    # Always generate fresh timestamp
    timestamp = datetime.now(timezone.utc).isoformat()

    return request_id, timestamp


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError):
        request_id, timestamp = _get_request_metadata(request)
        logger.warning(
            "domain_error",
            error_code=exc.code,
            status_code=exc.status_code,
            route=request.url.path,
        )
        lifecycle = classify_route_lifecycle(request.url.path).lifecycle.value
        migration_metrics.record_error_code(
            lifecycle=lifecycle,
            error_code=exc.code,
            status_code=exc.status_code,
        )
        payload = map_domain_error(exc, request_id, timestamp)
        return JSONResponse(
            status_code=exc.status_code,
            headers={"X-Request-ID": request_id},
            content=ErrorEnvelope(error=payload).model_dump(exclude_none=True),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        request_id, timestamp = _get_request_metadata(request)
        payload = map_validation_exception(exc, request_id, timestamp)
        logger.warning(
            "validation_error",
            error_code=payload.code,
            route=request.url.path,
        )
        lifecycle = classify_route_lifecycle(request.url.path).lifecycle.value
        migration_metrics.record_error_code(
            lifecycle=lifecycle,
            error_code=payload.code,
            status_code=422,
        )
        content = ErrorEnvelope(error=payload).model_dump(exclude_none=True)
        content["detail"] = exc.errors()
        return JSONResponse(
            status_code=422,
            headers={"X-Request-ID": request_id},
            content=content,
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException):
        request_id, timestamp = _get_request_metadata(request)
        payload = map_http_exception(exc, request_id, timestamp)
        logger.warning(
            "http_error",
            error_code=payload.code,
            status_code=exc.status_code,
            route=request.url.path,
        )
        lifecycle = classify_route_lifecycle(request.url.path).lifecycle.value
        migration_metrics.record_error_code(
            lifecycle=lifecycle,
            error_code=payload.code,
            status_code=exc.status_code,
        )
        content = ErrorEnvelope(error=payload).model_dump(exclude_none=True)
        if isinstance(exc.detail, str) or exc.detail is not None:
            content["detail"] = exc.detail
        return JSONResponse(
            status_code=exc.status_code,
            headers={"X-Request-ID": request_id},
            content=content,
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_error(request: Request, exc: Exception):
        request_id, timestamp = _get_request_metadata(request)
        payload = map_unhandled_exception(exc, request_id, timestamp)
        logger.error(
            "unhandled_error",
            error_code=payload.code,
            route=request.url.path,
            error=str(exc),
        )
        lifecycle = classify_route_lifecycle(request.url.path).lifecycle.value
        migration_metrics.record_error_code(
            lifecycle=lifecycle,
            error_code=payload.code,
            status_code=500,
        )
        return JSONResponse(
            status_code=500,
            headers={"X-Request-ID": request_id},
            content=ErrorEnvelope(error=payload).model_dump(exclude_none=True),
        )
