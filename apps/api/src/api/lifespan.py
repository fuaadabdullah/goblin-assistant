import asyncio
import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from .artifact_cleanup import artifact_cleanup_service
from .monitoring import monitor
from .secrets_router import cleanup_secrets_adapter, init_secrets_adapter
from .services.provider_health import health_monitor
from .storage.cache import cache
from .storage.database import init_db, is_postgres, warmup_pool

logger = structlog.get_logger()


async def _init_redis():
    try:
        await cache.init_redis()
        logger.info("Redis cache initialized")
    except Exception as exc:
        logger.warning(
            "Redis initialization failed",
            error=str(exc),
            impact="performance may be reduced",
        )


async def _init_db():
    try:
        db_initialized = await init_db()
        if db_initialized:
            if is_postgres:
                try:
                    await warmup_pool()
                    logger.info("Database pool warmed up")
                except Exception as exc:
                    logger.warning("Database pool warmup failed", error=str(exc))
            logger.info("Database initialized")
        else:
            logger.warning("Database initialization skipped", mode="limited")
    except Exception as exc:
        logger.warning(
            "Database initialization failed",
            error=str(exc),
            impact="some features may be limited",
        )


async def _start_provider_monitoring():
    try:
        await monitor.start()
        logger.info("Provider monitoring started")
    except Exception as exc:
        logger.warning("Provider monitoring failed to start", error=str(exc))


async def _start_ai_health_monitoring():
    try:
        await health_monitor.start()
        logger.info("AI provider health monitoring started")

        async def _validate():
            try:
                report = await health_monitor.validate_configured_credentials()
                invalid = report.get("invalid_credentials", [])
                unreachable = report.get("unreachable", [])
                if invalid:
                    logger.critical(
                        "Invalid AI provider credentials detected at startup",
                        invalid_providers=invalid,
                        action=(
                            "rotate/update provider keys; routing currently "
                            "fails over to other providers"
                        ),
                    )
                if unreachable:
                    logger.warning(
                        "Some configured AI providers are unreachable at startup",
                        unreachable_providers=unreachable,
                    )
                if invalid and os.getenv("FAIL_ON_PROVIDER_CREDENTIAL_ERRORS", "false").lower() in {
                    "1",
                    "true",
                    "yes",
                    "on",
                }:
                    logger.error(
                        "FAIL_ON_PROVIDER_CREDENTIAL_ERRORS is set but startup "
                        "already complete; manual restart required"
                    )
            except Exception as exc:
                logger.warning("Background credential validation failed", error=str(exc))

        asyncio.create_task(_validate())
    except Exception as exc:
        logger.warning(
            "AI provider health monitoring failed",
            error=str(exc),
            impact="routing may be degraded",
        )


async def _start_colab_heartbeat():
    try:
        from .services.colab_heartbeat import colab_heartbeat  # noqa: PLC0415

        await colab_heartbeat.start()
        logger.info("Colab worker heartbeat monitor started")
    except Exception as exc:
        logger.warning("Colab worker heartbeat monitor failed to start", error=str(exc))


async def _init_secrets():
    try:
        await init_secrets_adapter()
        logger.info("Secrets adapter initialized")
    except Exception as exc:
        logger.warning(
            "Failed to initialize secrets adapter",
            error=str(exc),
            impact="continuing without secrets management",
        )


async def _start_artifact_cleanup():
    try:
        await artifact_cleanup_service.start()
        logger.info("Artifact cleanup service started")
    except Exception as exc:
        logger.warning(
            "Artifact cleanup service failed to start",
            error=str(exc),
            impact="continuing without automatic cleanup",
        )


async def _start_embedding_worker():
    try:
        from .services.embedding_service import embedding_worker  # noqa: PLC0415

        await embedding_worker.start()
        logger.info("Embedding worker started")
    except Exception as exc:
        logger.warning(
            "Embedding worker failed to start",
            error=str(exc),
            impact="async message embedding will be unavailable",
        )


async def _restore_colab_endpoint():
    try:
        from .ops_routes.colab_worker import load_colab_endpoint_from_db  # noqa: PLC0415
        from .providers.dispatcher import dispatcher  # noqa: PLC0415

        saved_endpoint = await load_colab_endpoint_from_db()
        if saved_endpoint:
            dispatcher.update_provider_endpoint("colab_worker", saved_endpoint)
            logger.info("Colab worker endpoint restored", endpoint=saved_endpoint)
        else:
            logger.info("No saved Colab worker endpoint found")
    except Exception as exc:
        logger.warning("Failed to restore Colab worker endpoint", error=str(exc))


async def _stop_ai_health_monitoring():
    try:
        await health_monitor.stop()
        logger.info("AI provider health monitoring stopped")
    except Exception as exc:
        logger.warning("Failed to stop health monitoring", error=str(exc))


async def _stop_colab_heartbeat():
    try:
        from .services.colab_heartbeat import colab_heartbeat  # noqa: PLC0415

        await colab_heartbeat.stop()
        logger.info("Colab worker heartbeat monitor stopped")
    except Exception as exc:
        logger.warning("Failed to stop Colab heartbeat monitor", error=str(exc))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan: startup and shutdown logic."""
    try:
        logger.info("Starting Goblin Assistant API")

        # Group A: infrastructure (Redis + DB) in parallel
        await asyncio.gather(_init_redis(), _init_db())

        # Colab endpoint restore needs DB to be ready
        await _restore_colab_endpoint()

        # Group B: all monitoring/worker services in parallel;
        # credential validation runs as a background task inside _start_ai_health_monitoring
        await asyncio.gather(
            _start_provider_monitoring(),
            _start_ai_health_monitoring(),
            _start_colab_heartbeat(),
            _init_secrets(),
            _start_artifact_cleanup(),
            _start_embedding_worker(),
        )

        try:
            from .services import VECTOR_STORE_AVAILABLE  # noqa: PLC0415

            if VECTOR_STORE_AVAILABLE:
                logger.info("Safe vector store available")
            else:
                logger.warning(
                    "Safe vector store unavailable",
                    reason="sentence-transformers not installed",
                )
        except Exception:
            pass

        logger.info("Backend startup complete", status="ready")
    except Exception as exc:
        logger.error("Critical startup error", error=str(exc), action="application will restart")
        raise

    yield

    try:
        logger.info("Shutting down Goblin Assistant API")

        await asyncio.gather(
            _stop_ai_health_monitoring(),
            _stop_colab_heartbeat(),
        )

        await monitor.stop()
        logger.info("Provider monitoring stopped")

        await cache.close()
        logger.info("Redis cache closed")

        try:
            await cleanup_secrets_adapter()
            logger.info("Secrets adapter cleaned up")
        except Exception as exc:
            logger.warning("Failed to cleanup secrets adapter", error=str(exc))

        try:
            await artifact_cleanup_service.stop()
            logger.info("Artifact cleanup service stopped")
        except Exception as exc:
            logger.warning("Failed to stop artifact cleanup service", error=str(exc))

        try:
            from .services.embedding_service import embedding_worker  # noqa: PLC0415

            await embedding_worker.stop()
            logger.info("Embedding worker stopped")
        except Exception as exc:
            logger.warning("Failed to stop embedding worker", error=str(exc))

        logger.info("Backend shutdown complete")
    except Exception as exc:
        logger.error("Error during shutdown", error=str(exc))
