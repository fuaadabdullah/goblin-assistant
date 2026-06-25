"""
Middleware for Goblin Assistant API
Includes error handling, logging, and other cross-cutting concerns.
"""

import os
import time
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from api.core.contracts import ApiErrorPayload, ErrorEnvelope
from api.core.error_types import ErrorType

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

JWT_AUTH_ROUTE_PREFIXES = [
    "/api/v1/chat/contextual-chat",
    "/api/v1/chat/conversations",
    "/api/v1/chat/estimate-tokens",
    "/api/v1/chat/files",
    "/api/v1/chat/stream",
    "/api/v1/chat/upload-file",
]


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware to authenticate API requests using API key."""

    def __init__(self, app: ASGIApp, exclude_paths: list | None = None):
        super().__init__(app)

        # Check development mode upfront
        environment = os.getenv("ENVIRONMENT", "development").lower()
        is_development = environment in ["development", "dev", "local"]
        allow_unauth = os.getenv("ALLOW_UNAUTHENTICATED_REQUESTS", "false").lower() == "true"

        # Base excluded paths
        default_exclude = [
            "/docs",
            "/openapi.json",
            "/redoc",
            "/health",
            "/api/v1/health",
            "/api/v1/auth",
            "/sandbox",
            *JWT_AUTH_ROUTE_PREFIXES,
        ]

        # Merge provided paths with defaults
        if exclude_paths:
            base_paths = list(set(default_exclude + exclude_paths))
        else:
            base_paths = default_exclude

        # In development mode with ALLOW_UNAUTHENTICATED_REQUESTS, also exclude chat endpoints
        if is_development and allow_unauth:
            self.exclude_paths = base_paths + [
                "/api/v1/api/chat",
                "/api/v1/chat",
            ]
            self.exclude_paths = list(set(self.exclude_paths))  # Remove duplicates
        else:
            self.exclude_paths = base_paths

        self.api_key = os.getenv("LOCAL_LLM_API_KEY", "")
        self.allow_unauthenticated_requests = is_development and allow_unauth

    async def dispatch(self, request: Request, call_next):
        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        if self.allow_unauthenticated_requests:
            logger.warning(
                "SECURITY RISK: Allowing unauthenticated requests in development mode. "
                "Set ALLOW_UNAUTHENTICATED_REQUESTS=false to require authentication."
            )
            return await call_next(request)

        # Check for API key in headers
        api_key_header = request.headers.get("x-api-key") or request.headers.get("authorization")

        if api_key_header:
            # Handle Bearer token format
            if api_key_header.startswith("Bearer "):
                api_key_header = api_key_header[7:]  # Remove "Bearer " prefix

        if not self.api_key:
            # SECURITY: Check if we're in development mode
            request_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc).isoformat()

            logger.error(
                "SECURITY: No LOCAL_LLM_API_KEY configured and not in development bypass mode"
            )
            return JSONResponse(
                status_code=500,
                headers={"X-Request-ID": request_id},
                content=ErrorEnvelope(
                    error=ApiErrorPayload(
                        code="CONFIGURATION_ERROR",
                        type=ErrorType.AUTHENTICATION,
                        message="API authentication not configured",
                        request_id=request_id,
                        timestamp=timestamp,
                        details={"reason": "missing_api_key"},
                    )
                ).model_dump(exclude_none=True),
            )

        if not api_key_header or api_key_header != self.api_key:
            request_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc).isoformat()
            logger.warning(
                "Invalid or missing API key",
                client=request.client.host if request.client else "unknown",
                header_present=bool(api_key_header),
            )
            return JSONResponse(
                status_code=401,
                headers={"X-Request-ID": request_id},
                content=ErrorEnvelope(
                    error=ApiErrorPayload(
                        code="AUTHENTICATION_REQUIRED",
                        type=ErrorType.AUTHENTICATION,
                        message="Valid API key required",
                        request_id=request_id,
                        timestamp=timestamp,
                        details={"reason": "invalid_api_key"},
                    )
                ).model_dump(exclude_none=True),
            )

        # Authentication successful
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }

        # Add HSTS only for HTTPS (in production)
        environment = os.getenv("ENVIRONMENT", "development").lower()
        if environment == "production":
            self.security_headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Content Security Policy - restrict to self and trusted sources
        csp = "default-src 'self'; "
        csp += "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # Allow inline scripts for now
        csp += "style-src 'self' 'unsafe-inline'; "  # Allow inline styles
        csp += "img-src 'self' data: https:; "  # Allow data URLs and HTTPS images
        csp += "font-src 'self' data:; "  # Allow data URLs for fonts
        csp += "connect-src 'self' https: wss:; "  # Allow HTTPS and WSS connections
        csp += "frame-ancestors 'none';"  # Deny framing entirely

        self.security_headers["Content-Security-Policy"] = csp

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add security headers to response
        for header_name, header_value in self.security_headers.items():
            if header_name not in response.headers:
                response.headers[header_name] = header_value

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware to handle exceptions and return structured error responses."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = str(uuid.uuid4())

        # Add request context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )

        try:
            response = await call_next(request)

            # Log successful requests
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id

            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration=process_time,
            )

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                "request_failed",
                error=str(e),
                error_type=type(e).__name__,
                duration=process_time,
            )

            # In production, don't expose detailed error messages
            error_message = "An internal server error occurred"
            details = {}
            if os.getenv("DEBUG", "false").lower() == "true":
                error_message = str(e)
                details["error_class"] = type(e).__name__

            timestamp = datetime.now(timezone.utc).isoformat()

            return JSONResponse(
                status_code=500,
                headers={"X-Request-ID": request_id},
                content=ErrorEnvelope(
                    error=ApiErrorPayload(
                        code="INTERNAL_ERROR",
                        type=ErrorType.INTERNAL,
                        message=error_message,
                        request_id=request_id,
                        timestamp=timestamp,
                        details=details if details else None,
                    )
                ).model_dump(exclude_none=True),
            )
