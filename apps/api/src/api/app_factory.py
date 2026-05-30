import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import structlog

from .api_keys_router import router as api_keys_router
from .api_router import router as api_router
from .artifact_cleanup import artifact_cleanup_service  # noqa: F401
from .auth.router import router as auth_router
from .chat_router import router as chat_router
from .core.route_lifecycle import classify_route_lifecycle
from .exception_handlers import register_exception_handlers
from .health import router as health_router
from .lifespan import lifespan
from .middleware import AuthenticationMiddleware, ErrorHandlingMiddleware, SecurityHeadersMiddleware
from .observability.debug_router import router as observability_debug_router
from .observability.migration_metrics import migration_metrics
from .ops_router import router as ops_router
from .parse_router import router as parse_router
from .raptor_router import router as raptor_router
from .route_mounting import mount_primary_routes, mount_versioned_alias_routes
from .routes.account_router import router as account_router
from .routes.debug import router as model_suggestion_debug_router
from .routes.privacy import router as privacy_router
from .routes.providers_models import router as providers_models_router
from .routes.support_router import router as support_router
from .routing_router import router as routing_router
from .sandbox_api import router as sandbox_router
from .search_router import router as search_router
from .security_config import SecurityConfig
from .secrets_router import router as secrets_router
from .semantic_chat_router import router as semantic_chat_router
from .settings_router import router as settings_router
from .stream_router import router as stream_router
from .write_time_router import router as write_time_router

logger = structlog.get_logger()


def _parse_sample_rate(raw_value: str, fallback: float) -> float:
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return fallback
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _is_true(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_env_files() -> None:
    try:
        from dotenv import load_dotenv

        current_dir = Path(__file__).resolve()
        repo_root = current_dir.parents[4]
        env_local = repo_root / ".env.local"
        env_file = repo_root / ".env"

        if env_local.exists():
            load_dotenv(str(env_local))
        if env_file.exists():
            load_dotenv(str(env_file))
    except ImportError:
        logger.warning("python-dotenv not installed, skipping .env loading", component="startup")


def _init_sentry() -> None:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        from .services.sentry_hooks import sentry_before_breadcrumb, sentry_before_send

        sentry_dsn = os.getenv("SENTRY_DSN")
        if not sentry_dsn:
            raise RuntimeError("SENTRY_DSN not configured, skipping Sentry init")

        sentry_environment = os.getenv("ENVIRONMENT", "development").lower()
        default_traces_rate = 0.1 if sentry_environment == "production" else 1.0
        default_profiles_rate = 0.01 if sentry_environment == "production" else 1.0

        traces_sample_rate = _parse_sample_rate(
            os.getenv("SENTRY_TRACES_SAMPLE_RATE", str(default_traces_rate)),
            default_traces_rate,
        )
        profiles_sample_rate = _parse_sample_rate(
            os.getenv("SENTRY_PROFILES_SAMPLE_RATE", str(default_profiles_rate)),
            default_profiles_rate,
        )

        sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=profiles_sample_rate,
            send_default_pii=False,
            before_send=sentry_before_send,
            before_breadcrumb=sentry_before_breadcrumb,
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
            ],
            environment=sentry_environment,
            release=os.getenv("RELEASE_VERSION", "goblin-assistant@1.0.0"),
        )
        logger.info(
            "Sentry SDK initialized",
            provider="sentry",
            error_monitoring="enabled",
            environment=sentry_environment,
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=profiles_sample_rate,
            send_default_pii=False,
        )
    except ImportError:
        logger.warning(
            "Sentry SDK not available",
            reason="package not installed",
            suggestion="pip install sentry-sdk",
        )
    except RuntimeError:
        logger.warning("Sentry error monitoring disabled", reason="SENTRY_DSN not set")
    except Exception as exc:
        logger.warning("Failed to initialize Sentry SDK", error=str(exc))


def _resolve_routing_analytics_router():
    try:
        from .routes.routing_analytics import router as routing_analytics_router

        return True, routing_analytics_router
    except ImportError:
        return False, None


async def add_contract_lifecycle_headers(request: Request, call_next):
    correlation_id = request.headers.get("x-correlation-id") or request.headers.get("x-request-id")
    response = await call_next(request)
    decision = classify_route_lifecycle(request.url.path)
    response.headers["X-API-Lifecycle"] = decision.lifecycle.value
    if decision.sunset_at:
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = decision.sunset_at
    if correlation_id:
        response.headers["X-Correlation-ID"] = correlation_id
    migration_metrics.record_request(
        path=request.url.path,
        lifecycle=decision.lifecycle.value,
        is_v1=request.url.path.startswith("/api/v1"),
        status_code=response.status_code,
    )
    return response


def create_app() -> FastAPI:
    _load_env_files()
    _init_sentry()
    routing_analytics_available, routing_analytics_router = _resolve_routing_analytics_router()

    app = FastAPI(
        title="Goblin Assistant API",
        description="AI-powered development assistant with multi-provider routing",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.middleware("http")(add_contract_lifecycle_headers)

    register_exception_handlers(app)

    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    environment = os.getenv("ENVIRONMENT", "development").lower()
    rate_limit_enabled_raw = os.getenv("RATE_LIMIT_ENABLED")
    if rate_limit_enabled_raw is None:
        rate_limit_enabled = environment == "production"
    else:
        rate_limit_enabled = _is_true(rate_limit_enabled_raw)

    if rate_limit_enabled:
        try:
            from .middleware.rate_limiter import RateLimiter

            requests_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
            requests_per_hour = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
            rate_limiter = RateLimiter(
                redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
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
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
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
            "/api/chat",
            "/api/v1/api/chat",
            "/chat",
            "/sandbox",
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

    mount_primary_routes(
        app,
        api_router=api_router,
        auth_router=auth_router,
        routing_router=routing_router,
        parse_router=parse_router,
        raptor_router=raptor_router,
        api_keys_router=api_keys_router,
        settings_router=settings_router,
        search_router=search_router,
        stream_router=stream_router,
        chat_router=chat_router,
        semantic_chat_router=semantic_chat_router,
        write_time_router=write_time_router,
        health_router=health_router,
        ops_router=ops_router,
        secrets_router=secrets_router,
        privacy_router=privacy_router,
        model_suggestion_debug_router=model_suggestion_debug_router,
        observability_debug_router=observability_debug_router,
        sandbox_router=sandbox_router,
        providers_models_router=providers_models_router,
        account_router=account_router,
        support_router=support_router,
        routing_analytics_available=routing_analytics_available,
        routing_analytics_router=routing_analytics_router,
    )

    mount_versioned_alias_routes(
        app,
        health_router=health_router,
        settings_router=settings_router,
        providers_models_router=providers_models_router,
        chat_router=chat_router,
        api_router=api_router,
        auth_router=auth_router,
        search_router=search_router,
        sandbox_router=sandbox_router,
        account_router=account_router,
        support_router=support_router,
    )

    @app.get("/")
    async def root():
        return {
            "message": "Goblin Assistant API",
            "version": app.version,
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/test")
    async def test_endpoint():
        return {"message": "Server is working", "status": "ok"}

    return app
