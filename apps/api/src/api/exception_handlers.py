from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import structlog

from .core.contracts import ErrorEnvelope
from .core.errors import (
    DomainError,
    map_http_exception,
    map_unhandled_exception,
    map_validation_exception,
)
from .core.route_lifecycle import classify_route_lifecycle
from .observability.migration_metrics import migration_metrics

logger = structlog.get_logger()


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError):
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
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorEnvelope(
                error={"code": exc.code, "message": exc.message, "details": exc.details}
            ).model_dump(exclude_none=True),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        payload = map_validation_exception(exc)
        logger.warning("validation_error", error_code=payload.code, route=request.url.path)
        lifecycle = classify_route_lifecycle(request.url.path).lifecycle.value
        migration_metrics.record_error_code(
            lifecycle=lifecycle,
            error_code=payload.code,
            status_code=422,
        )
        return JSONResponse(
            status_code=422,
            content=ErrorEnvelope(error=payload).model_dump(exclude_none=True),
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException):
        payload = map_http_exception(exc)
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
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorEnvelope(error=payload).model_dump(exclude_none=True),
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_error(request: Request, exc: Exception):
        payload = map_unhandled_exception(exc)
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
            content=ErrorEnvelope(error=payload).model_dump(exclude_none=True),
        )
