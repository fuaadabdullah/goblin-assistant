from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional, Tuple

import structlog

logger = structlog.get_logger()


def parse_sample_rate(raw_value: str, fallback: float) -> float:
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return fallback
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def is_true(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_env_files() -> None:
    try:
        from dotenv import load_dotenv

        current_dir = Path(__file__).resolve()
        repo_root = current_dir.parents[5]
        env_local = repo_root / ".env.local"
        env_file = repo_root / ".env"

        if env_local.exists():
            load_dotenv(str(env_local))
        if env_file.exists():
            load_dotenv(str(env_file))
    except ImportError:
        logger.warning("python-dotenv not installed, skipping .env loading", component="startup")


def init_sentry() -> None:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        from ..services.sentry_hooks import sentry_before_breadcrumb, sentry_before_send

        sentry_dsn = os.getenv("SENTRY_DSN")
        if not sentry_dsn:
            raise RuntimeError("SENTRY_DSN not configured, skipping Sentry init")

        sentry_environment = os.getenv("ENVIRONMENT", "development").lower()
        default_traces_rate = 0.1 if sentry_environment == "production" else 1.0
        default_profiles_rate = 0.01 if sentry_environment == "production" else 1.0

        traces_sample_rate = parse_sample_rate(
            os.getenv("SENTRY_TRACES_SAMPLE_RATE", str(default_traces_rate)),
            default_traces_rate,
        )
        profiles_sample_rate = parse_sample_rate(
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


def resolve_optional_routing_analytics_router() -> Tuple[bool, Optional[Any]]:
    try:
        from ..routes.routing_analytics import router as routing_analytics_router

        return True, routing_analytics_router
    except ImportError:
        return False, None
