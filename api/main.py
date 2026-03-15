#!/usr/bin/env python3
"""
Main FastAPI application for Goblin Assistant
Combines all the routers into a single application
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import structlog

# Import all routers (use package-qualified imports so tests can import api.main)
from .api_router import router as api_router
from .auth.router import router as auth_router
from .routing_router import router as routing_router
from .parse_router import router as parse_router
from .raptor_router import router as raptor_router

# Import middlewares (from middleware.py file, not middleware/ package)
from .middleware import (
    AuthenticationMiddleware,
    SecurityHeadersMiddleware,
    ErrorHandlingMiddleware,
)

from .chat_router import router as chat_router
from .semantic_chat_router import router as semantic_chat_router
from .write_time_router import router as write_time_router
from .health import router as health_router
from .ops_router import router as ops_router
from .api_keys_router import router as api_keys_router
from .settings_router import router as settings_router
from .search_router import router as search_router
from .stream_router import router as stream_router
from .routes.privacy import router as privacy_router  # Updated to new location
from .routes.debug import router as model_suggestion_debug_router  # Model suggestion endpoint
from .secrets_router import (
    router as secrets_router,
    init_secrets_adapter,
    cleanup_secrets_adapter,
)
from .observability.debug_router import router as observability_debug_router  # Renamed for clarity
from .sandbox_api import router as sandbox_router
from .routes.providers_models import router as providers_models_router
from .routes.account_router import router as account_router
from .routes.support_router import router as support_router
from .storage.cache import cache
from .storage.database import init_db

from .monitoring import monitor
from .artifact_cleanup import artifact_cleanup_service
from .security_config import SecurityConfig

# Initialize structured logger (early, for use in module-level initialization)
logger = structlog.get_logger()


def _parse_sample_rate(raw_value: str, fallback: float) -> float:
    """Parse and clamp sample rate into [0.0, 1.0], with fallback on invalid input."""
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return fallback

    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value

# Load environment variables from .env.local if it exists
try:
    from dotenv import load_dotenv
    import pathlib

    # Get the directory of this file (goblin-assistant directory)
    current_dir = pathlib.Path(__file__).parent.parent

    # Try to load .env files from the goblin-assistant root
    env_local = current_dir / ".env.local"
    env_file = current_dir / ".env"

    if env_local.exists():
        load_dotenv(str(env_local))
    if env_file.exists():
        load_dotenv(str(env_file))
except ImportError:
    # dotenv not available, continue without it
    logger.warning(
        "python-dotenv not installed, skipping .env loading",
        component="startup",
    )

# Initialize Sentry for error monitoring
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
        # Enable performance monitoring
        traces_sample_rate=traces_sample_rate,
        # Enable profiling
        profiles_sample_rate=profiles_sample_rate,
        # Privacy-first defaults
        send_default_pii=False,
        before_send=sentry_before_send,
        before_breadcrumb=sentry_before_breadcrumb,
        # Integrations
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        # Environment
        environment=sentry_environment,
        # Release tracking
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
    logger.warning("Sentry SDK not available", reason="package not installed", suggestion="pip install sentry-sdk")
except RuntimeError:
    logger.warning("Sentry error monitoring disabled", reason="SENTRY_DSN not set")
except Exception as e:
    logger.warning("Failed to initialize Sentry SDK", error=str(e))

# Import routing analytics router (new)
try:
    from .routes.routing_analytics import router as routing_analytics_router

    ROUTING_ANALYTICS_AVAILABLE = True
except ImportError:
    ROUTING_ANALYTICS_AVAILABLE = False
    routing_analytics_router = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown logic."""
    # --- Startup ---
    try:
        logger.info("Starting Goblin Assistant API")

        # Initialize Redis cache
        logger.info("Initializing Redis cache")
        try:
            await cache.init_redis()
            logger.info("Redis cache initialized")
        except Exception as e:
            logger.warning("Redis initialization failed", error=str(e), impact="performance may be reduced")

        # Initialize database tables (optional for now)
        logger.info("Checking database availability")
        try:
            db_initialized = await init_db()
            if db_initialized:
                logger.info("Database initialized")
            else:
                logger.warning("Database initialization skipped", mode="limited")
        except Exception as e:
            logger.warning("Database initialization failed", error=str(e), impact="some features may be limited")

        # Start provider monitoring
        logger.info("Starting provider monitoring")
        try:
            await monitor.start()
            logger.info("Provider monitoring started")
        except Exception as e:
            logger.warning("Provider monitoring failed to start", error=str(e))

        # Start AI provider health monitoring (smart routing)
        logger.info("Starting AI provider health monitoring")
        try:
            from .services.provider_health import health_monitor

            await health_monitor.start()
            logger.info("AI provider health monitoring started")

            # One-shot credential validation so invalid cloud keys are surfaced loudly.
            provider_credential_report = (
                await health_monitor.validate_configured_credentials()
            )
            invalid_credentials = provider_credential_report["invalid_credentials"]
            unreachable_providers = provider_credential_report["unreachable"]

            if invalid_credentials:
                logger.critical(
                    "Invalid AI provider credentials detected at startup",
                    invalid_providers=invalid_credentials,
                    action=(
                        "rotate/update provider keys; routing currently fails over "
                        "to other providers"
                    ),
                )

            if unreachable_providers:
                logger.warning(
                    "Some configured AI providers are unreachable at startup",
                    unreachable_providers=unreachable_providers,
                )

            if invalid_credentials and os.getenv(
                "FAIL_ON_PROVIDER_CREDENTIAL_ERRORS", "false"
            ).lower() in {"1", "true", "yes", "on"}:
                raise RuntimeError(
                    "Invalid provider credentials found during startup validation"
                )
        except Exception as e:
            logger.warning("AI provider health monitoring failed", error=str(e), impact="routing may be degraded")

        # Initialize secrets adapter
        logger.info("Initializing secrets adapter")
        try:
            await init_secrets_adapter()
            logger.info("Secrets adapter initialized")
        except Exception as e:
            logger.warning("Failed to initialize secrets adapter", error=str(e), impact="continuing without secrets management")

        # Check privacy features
        logger.info("Checking privacy and security features")
        try:
            from .services.sanitization import sanitize_input_for_model
            from .services.telemetry import log_inference_metrics

            logger.info("PII sanitization available")
            logger.info("Telemetry with redaction available")
        except Exception as e:
            logger.warning("Privacy features not fully loaded", error=str(e))

        try:
            from .services import VECTOR_STORE_AVAILABLE

            if VECTOR_STORE_AVAILABLE:
                logger.info("Safe vector store available")
            else:
                logger.warning("Safe vector store unavailable", reason="sentence-transformers not installed")
        except Exception:
            pass

        # Start artifact cleanup service
        logger.info("Starting artifact cleanup service")
        try:
            await artifact_cleanup_service.start()
            logger.info("Artifact cleanup service started")
        except Exception as e:
            logger.warning("Artifact cleanup service failed to start", error=str(e), impact="continuing without automatic cleanup")

        logger.info("Backend startup complete", status="ready")

    except Exception as e:
        logger.error("Critical startup error", error=str(e), action="application will restart")
        raise

    yield  # Application runs here

    # --- Shutdown ---
    try:
        logger.info("Shutting down Goblin Assistant API")

        # Stop AI provider health monitoring
        logger.info("Stopping AI provider health monitoring")
        try:
            from .services.provider_health import health_monitor

            await health_monitor.stop()
            logger.info("AI provider health monitoring stopped")
        except Exception as e:
            logger.warning("Failed to stop health monitoring", error=str(e))

        logger.info("Stopping provider monitoring")
        await monitor.stop()
        logger.info("Provider monitoring stopped")

        logger.info("Closing Redis cache")
        await cache.close()
        logger.info("Redis cache closed")

        logger.info("Cleaning up secrets adapter")
        try:
            await cleanup_secrets_adapter()
            logger.info("Secrets adapter cleaned up")
        except Exception as e:
            logger.warning("Failed to cleanup secrets adapter", error=str(e))

        logger.info("Stopping artifact cleanup service")
        try:
            await artifact_cleanup_service.stop()
            logger.info("Artifact cleanup service stopped")
        except Exception as e:
            logger.warning("Failed to stop artifact cleanup service", error=str(e))

        logger.info("Backend shutdown complete")

    except Exception as e:
        logger.error("Error during shutdown", error=str(e))
        # Don't raise here as we're shutting down


# Create FastAPI app
app = FastAPI(
    title="Goblin Assistant API",
    description="AI-powered development assistant with multi-provider routing",
    version="1.0.0",
    lifespan=lifespan,
)


# Add Error Handling middleware
app.add_middleware(ErrorHandlingMiddleware)

# Add Security Headers middleware
app.add_middleware(SecurityHeadersMiddleware)


def _is_true(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


environment = os.getenv("ENVIRONMENT", "development").lower()
rate_limit_enabled_raw = os.getenv("RATE_LIMIT_ENABLED")
if rate_limit_enabled_raw is None:
    rate_limit_enabled = environment == "production"
else:
    rate_limit_enabled = _is_true(rate_limit_enabled_raw)

# Add Rate Limiting middleware for privacy/security (requires Redis)
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
    except Exception as e:
        logger.warning("Rate limiting disabled", error=str(e))
else:
    logger.warning(
        "Rate limiting middleware disabled by configuration",
        environment=environment,
    )

# Add Authentication middleware
app.add_middleware(
    AuthenticationMiddleware,
    exclude_paths=[
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/auth/register",
        "/auth/login",
        "/auth/validate",
        "/auth/oauth/google",
        "/auth/oauth/google/callback",
        "/auth/passkey/register",
        "/auth/passkey/authenticate",
        "/api/chat",  # Allow chat API in development
        "/chat",  # Allow chat routes in development
        "/sandbox",  # Allow sandbox API in development
    ],
)

# Add CORS middleware
allowed_origins = list(SecurityConfig.ALLOWED_ORIGINS)
if environment == "production" and not os.getenv("ALLOWED_ORIGINS"):
    logger.warning(
        "No ALLOWED_ORIGINS configured for production",
        action="setting fallback origins",
        severity="security_warning",
    )

if "*" in allowed_origins:
    logger.warning("CORS configured to allow all origins", environment="*", severity="security_risk", note="acceptable only for development")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"] if environment != "production" else SecurityConfig.ALLOWED_HEADERS,
)

# Include all routers
app.include_router(api_router)
app.include_router(auth_router)
app.include_router(routing_router)
app.include_router(parse_router)
app.include_router(raptor_router)
app.include_router(api_keys_router)
app.include_router(settings_router)
app.include_router(search_router)
app.include_router(stream_router)
app.include_router(chat_router)
app.include_router(semantic_chat_router)
app.include_router(write_time_router)
app.include_router(health_router)
app.include_router(ops_router)
app.include_router(secrets_router)
app.include_router(privacy_router)  # GDPR/CCPA compliance
app.include_router(model_suggestion_debug_router)  # Model-based debug suggestions
app.include_router(observability_debug_router)  # Observability & diagnostic surfaces
app.include_router(sandbox_router)  # Secure code execution sandbox
app.include_router(providers_models_router)  # Provider and model discovery
app.include_router(account_router)  # User account management
app.include_router(support_router)  # User support/feedback

# Include routing analytics router (new smart routing)
if ROUTING_ANALYTICS_AVAILABLE and routing_analytics_router:
    app.include_router(routing_analytics_router)


@app.get("/")
async def root():
    """Lightweight service metadata endpoint kept for API compatibility."""
    return {
        "message": "Goblin Assistant API",
        "version": app.version,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/test")
async def test_endpoint():
    """Simple test endpoint without database"""
    return {"message": "Server is working", "status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
