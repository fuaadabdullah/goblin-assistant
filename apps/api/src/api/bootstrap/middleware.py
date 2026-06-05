from __future__ import annotations

import os
from typing import Callable

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from ..core.route_lifecycle import classify_route_lifecycle
from ..middleware import (
    AuthenticationMiddleware,
    ErrorHandlingMiddleware,
    SecurityHeadersMiddleware,
)
from ..observability.migration_metrics import migration_metrics
from ..security_config import SecurityConfig
from .startup import is_true

logger = structlog.get_logger()


async def add_contract_lifecycle_headers(request: Request, call_next: Callable):
    correlation_id = request.headers.get("x-correlation-id") or request.headers.get("x-request-id")
    response = await call_next(request)
    lifecycle_path = str(request.scope.get("goblin.original_path", request.url.path))
    decision = classify_route_lifecycle(lifecycle_path)
    response.headers["X-API-Lifecycle"] = decision.lifecycle.value
    if decision.sunset_at:
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = decision.sunset_at
    if correlation_id:
        response.headers["X-Correlation-ID"] = correlation_id
    migration_metrics.record_request(
        path=lifecycle_path,
        lifecycle=decision.lifecycle.value,
        is_v1=request.url.path.startswith("/api/v1"),
        status_code=response.status_code,
    )
    return response


def install_runtime_middlewares(app: FastAPI, *, environment: str) -> None:
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    rate_limit_enabled_raw = os.getenv("RATE_LIMIT_ENABLED")
    if rate_limit_enabled_raw is None:
        rate_limit_enabled = True
    else:
        rate_limit_enabled = is_true(rate_limit_enabled_raw)

    if rate_limit_enabled:
        try:
            from ..middleware.rate_limiter import RateLimiter

            requests_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
            requests_per_hour = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
            rate_limiter = RateLimiter(
                requests_per_minute=requests_per_minute,
                requests_per_hour=requests_per_hour,
            )
            app.middleware("http")(rate_limiter)
            logger.info(
                "Rate limiting middleware enabled",
                requests_per_minute=requests_per_minute,
                requests_per_hour=requests_per_hour,
                environment=environment,
            )
        except ImportError:
            logger.warning(
                "Rate limiting unavailable",
                reason="redis package not installed",
                suggestion="pip install redis",
            )
        except Exception as exc:
            logger.warning("Rate limiting disabled", error=str(exc))
    else:
        logger.warning(
            "Rate limiting middleware disabled by configuration",
            environment=environment,
        )

    app.add_middleware(
        AuthenticationMiddleware,
        exclude_paths=[
            "/docs",
            "/openapi.json",
            "/redoc",
            "/api/v1/health",
            "/auth/register",
            "/auth/login",
            "/auth/csrf-token",
            "/auth/google/url",
            "/auth/google/callback",
            "/auth/validate",
            "/auth/refresh",
            "/auth/oauth/google",
            "/auth/oauth/google/callback",
            "/auth/passkey/challenge",
            "/auth/passkey/register",
            "/auth/passkey/auth",
            "/auth/passkey/authenticate",
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/auth/csrf-token",
            "/api/v1/auth/google/url",
            "/api/v1/auth/google/callback",
            "/api/v1/auth/validate",
            "/api/v1/auth/refresh",
            "/api/v1/auth/oauth/google",
            "/api/v1/auth/oauth/google/callback",
            "/api/v1/auth/passkey/challenge",
            "/api/v1/auth/passkey/register",
            "/api/v1/auth/passkey/auth",
            "/api/v1/auth/passkey/authenticate",
            "/api/v1/api/chat",
            "/api/v1/sandbox",
        ],
    )

    allowed_origins = list(SecurityConfig.ALLOWED_ORIGINS)
    if environment == "production" and not os.getenv("ALLOWED_ORIGINS"):
        logger.warning(
            "No ALLOWED_ORIGINS configured for production",
            action="setting fallback origins",
            severity="security_warning",
        )

    if "*" in allowed_origins:
        logger.warning(
            "CORS configured to allow all origins",
            environment="*",
            severity="security_risk",
            note="acceptable only for development",
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=(["*"] if environment != "production" else SecurityConfig.ALLOWED_HEADERS),
    )
