from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from structlog.contextvars import bind_contextvars, clear_contextvars

from ..config.settings import get_settings
from ..core.route_lifecycle import LifecycleDecision, RouteLifecycle, classify_route_lifecycle
from ..middleware import (
    AuthenticationMiddleware,
    ErrorHandlingMiddleware,
    SecurityHeadersMiddleware,
)
from ..observability.migration_metrics import migration_metrics
from ..security_config import SecurityConfig

logger = structlog.get_logger()


async def structured_request_logging(request: Request, call_next):
    """Bind request context for every log emitted during an HTTP request."""
    request_id = request.headers.get("x-request-id") or request.headers.get("x-correlation-id")
    if not request_id:
        request_id = str(uuid.uuid4())
    clear_contextvars()
    bind_contextvars(request_id=request_id, method=request.method, path=request.url.path)
    started = time.perf_counter()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "http_request",
            status_code=response.status_code,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return response
    except Exception:
        logger.exception("http_request_failed")
        raise
    finally:
        clear_contextvars()


def resolve_runtime_origins(*, environment: str, configured: list[str]) -> list[str]:
    """Enforce the production CORS origin policy at startup (fail fast).

    Production refuses to boot without an explicit ``ALLOWED_ORIGINS`` (or
    ``FRONTEND_URL``/``BACKEND_URL``) setting — even though canonical fallbacks
    from :mod:`api.security_config` exist — and rejects a ``"*"`` wildcard
    combined with ``allow_credentials=True``. Non-production environments keep
    the permissive behavior for local development.
    """
    if environment != "production":
        return configured
    if "*" in configured:
        raise RuntimeError(
            "Refusing to start: CORS wildcard origin ('*') is not allowed in production. "
            "Set ALLOWED_ORIGINS to explicit origins."
        )
    if not configured:
        raise RuntimeError(
            "Refusing to start: no CORS origins resolved for production. "
            "Set ALLOWED_ORIGINS (or FRONTEND_URL/BACKEND_URL) to explicit origins."
        )
    settings = get_settings()
    explicit = settings.allowed_origins or (
        settings.frontend_url
        if settings.frontend_url != "http://localhost:3000"
        else settings.backend_url
        if settings.backend_url != "http://localhost:8004"
        else ""
    )
    if not explicit:
        raise RuntimeError(
            "Refusing to start: no explicit ALLOWED_ORIGINS (or FRONTEND_URL/BACKEND_URL) "
            "configured for production. Set explicit origins; canonical fallbacks are not "
            "sufficient evidence of operator intent."
        )
    return configured


async def add_contract_lifecycle_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
):
    correlation_id = request.headers.get("x-correlation-id") or request.headers.get("x-request-id")
    response = await call_next(request)
    lifecycle_path = str(request.scope.get("goblin.original_path", request.url.path))
    decision = classify_route_lifecycle(lifecycle_path)
    route = request.scope.get("route")
    route_deprecated = bool(getattr(route, "deprecated", False))
    route_extra = getattr(route, "openapi_extra", None) or {}
    if route_deprecated and decision.lifecycle == RouteLifecycle.STABLE:
        decision = LifecycleDecision(
            lifecycle=RouteLifecycle.LEGACY,
            sunset_at=str(route_extra.get("x-goblin-sunset-at", "")).strip() or None,
        )
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
    app.middleware("http")(structured_request_logging)
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    settings = get_settings()
    if settings.rate_limit_enabled is None:
        rate_limit_enabled = True
    else:
        rate_limit_enabled = settings.rate_limit_enabled

    if rate_limit_enabled:
        try:
            from ..middleware.rate_limiter import RateLimiter

            requests_per_minute = settings.rate_limit_per_minute
            requests_per_hour = settings.rate_limit_per_hour
            rate_limiter = RateLimiter(
                requests_per_minute=requests_per_minute,
                requests_per_hour=requests_per_hour,
                environment=environment,
            )
            app.middleware("http")(rate_limiter)
            logger.info(
                "Rate limiting middleware enabled",
                requests_per_minute=requests_per_minute,
                requests_per_hour=requests_per_hour,
                environment=environment,
            )
        except ImportError:
            if environment == "production":
                raise RuntimeError(
                    "Refusing to start: rate limiting is required in production but the "
                    "redis package is not installed (pip install redis)."
                )
            logger.warning(
                "Rate limiting unavailable",
                reason="redis package not installed",
                suggestion="pip install redis",
            )
        except RuntimeError:
            raise
        except Exception as exc:
            if environment == "production":
                raise RuntimeError(
                    f"Refusing to start: rate limiter failed to initialize: {exc}"
                ) from exc
            logger.warning("Rate limiting disabled", error=str(exc))
    else:
        if environment == "production":
            raise RuntimeError(
                "Refusing to start: RATE_LIMIT_ENABLED=false is not allowed in production. "
                "Rate limiting must stay enabled."
            )
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
            "/test",
            "/health",
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
            "/api/v1/sandbox",
            # NOTE: /api/v1/api/chat is intentionally NOT excluded here: it
            # requires the machine API key via AuthenticationMiddleware.
            # /api/v1/sandbox keeps the legacy bootstrap-level exclusion and
            # enforces X-Api-Key per-route via require_api_key in sandbox_api.
            # See api/middleware/http.py default exclusions.
        ],
    )

    allowed_origins = list(SecurityConfig.ALLOWED_ORIGINS)
    if environment == "production":
        resolve_runtime_origins(environment=environment, configured=allowed_origins)

    if "*" in allowed_origins and environment != "production":
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
