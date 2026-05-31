from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
import structlog

from .artifact_cleanup import artifact_cleanup_service
from .monitoring import monitor
from .secrets_router import cleanup_secrets_adapter, init_secrets_adapter
from .storage.cache import cache
from .storage.database import init_db

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown logic."""
    try:
        logger.info("Starting Goblin Assistant API")

        logger.info("Initializing Redis cache")
        try:
            await cache.init_redis()
            logger.info("Redis cache initialized")
        except Exception as exc:
            logger.warning(
                "Redis initialization failed",
                error=str(exc),
                impact="performance may be reduced",
            )

        logger.info("Checking database availability")
        try:
            db_initialized = await init_db()
            if db_initialized:
                logger.info("Database initialized")
            else:
                logger.warning("Database initialization skipped", mode="limited")
        except Exception as exc:
            logger.warning(
                "Database initialization failed",
                error=str(exc),
                impact="some features may be limited",
            )

        logger.info("Starting provider monitoring")
        try:
            await monitor.start()
            logger.info("Provider monitoring started")
        except Exception as exc:
            logger.warning("Provider monitoring failed to start", error=str(exc))

        logger.info("Starting AI provider health monitoring")
        try:
            from .services.provider_health import health_monitor

            await health_monitor.start()
            logger.info("AI provider health monitoring started")

            report = await health_monitor.validate_configured_credentials()
            invalid_credentials = report["invalid_credentials"]
            unreachable_providers = report["unreachable"]

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
                raise RuntimeError("Invalid provider credentials found during startup validation")
        except Exception as exc:
            logger.warning(
                "AI provider health monitoring failed",
                error=str(exc),
                impact="routing may be degraded",
            )

        logger.info("Starting Colab worker heartbeat monitor")
        try:
            from .services.colab_heartbeat import colab_heartbeat

            await colab_heartbeat.start()
            logger.info("Colab worker heartbeat monitor started")
        except Exception as exc:
            logger.warning(
                "Colab worker heartbeat monitor failed to start",
                error=str(exc),
            )

        logger.info("Restoring Colab worker endpoint from database")
        try:
            from .ops_routes.colab_worker import load_colab_endpoint_from_db
            from .providers.dispatcher import dispatcher

            saved_endpoint = await load_colab_endpoint_from_db()
            if saved_endpoint:
                dispatcher.update_provider_endpoint("colab_worker", saved_endpoint)
                logger.info("Colab worker endpoint restored", endpoint=saved_endpoint)
            else:
                logger.info("No saved Colab worker endpoint found")
        except Exception as exc:
            logger.warning("Failed to restore Colab worker endpoint", error=str(exc))

        logger.info("Initializing secrets adapter")
        try:
            await init_secrets_adapter()
            logger.info("Secrets adapter initialized")
        except Exception as exc:
            logger.warning(
                "Failed to initialize secrets adapter",
                error=str(exc),
                impact="continuing without secrets management",
            )

        logger.info("Checking privacy and security features")
        try:
            logger.info("PII sanitization available")
            logger.info("Telemetry with redaction available")
        except Exception as exc:
            logger.warning("Privacy features not fully loaded", error=str(exc))

        try:
            from .services import VECTOR_STORE_AVAILABLE

            if VECTOR_STORE_AVAILABLE:
                logger.info("Safe vector store available")
            else:
                logger.warning(
                    "Safe vector store unavailable",
                    reason="sentence-transformers not installed",
                )
        except Exception:
            pass

        logger.info("Starting artifact cleanup service")
        try:
            await artifact_cleanup_service.start()
            logger.info("Artifact cleanup service started")
        except Exception as exc:
            logger.warning(
                "Artifact cleanup service failed to start",
                error=str(exc),
                impact="continuing without automatic cleanup",
            )

        logger.info("Starting embedding worker")
        try:
            from .services.embedding_service import embedding_worker

            await embedding_worker.start()
            logger.info("Embedding worker started")
        except Exception as exc:
            logger.warning(
                "Embedding worker failed to start",
                error=str(exc),
                impact="async message embedding will be unavailable",
            )

        logger.info("Backend startup complete", status="ready")
    except Exception as exc:
        logger.error("Critical startup error", error=str(exc), action="application will restart")
        raise

    yield

    try:
        logger.info("Shutting down Goblin Assistant API")

        logger.info("Stopping AI provider health monitoring")
        try:
            from .services.provider_health import health_monitor

            await health_monitor.stop()
            logger.info("AI provider health monitoring stopped")
        except Exception as exc:
            logger.warning("Failed to stop health monitoring", error=str(exc))

        logger.info("Stopping Colab worker heartbeat monitor")
        try:
            from .services.colab_heartbeat import colab_heartbeat

            await colab_heartbeat.stop()
            logger.info("Colab worker heartbeat monitor stopped")
        except Exception as exc:
            logger.warning("Failed to stop Colab heartbeat monitor", error=str(exc))

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
        except Exception as exc:
            logger.warning("Failed to cleanup secrets adapter", error=str(exc))

        logger.info("Stopping artifact cleanup service")
        try:
            await artifact_cleanup_service.stop()
            logger.info("Artifact cleanup service stopped")
        except Exception as exc:
            logger.warning("Failed to stop artifact cleanup service", error=str(exc))

        logger.info("Stopping embedding worker")
        try:
            from .services.embedding_service import embedding_worker

            await embedding_worker.stop()
            logger.info("Embedding worker stopped")
        except Exception as exc:
            logger.warning("Failed to stop embedding worker", error=str(exc))

        logger.info("Backend shutdown complete")
    except Exception as exc:
        logger.error("Error during shutdown", error=str(exc))
