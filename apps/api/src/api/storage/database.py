"""Database connection management for Goblin Assistant."""

import os
import ssl
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from urllib.parse import parse_qs, urlencode

import structlog
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool

logger = structlog.get_logger()

SQLITE_DATABASE_URL = "sqlite+aiosqlite:///./goblin_assistant.db"
POSTGRES_ASYNC_URL_PREFIX = "postgresql+asyncpg://"

# Get database URL from environment or use local sqlite fallback.
DATABASE_URL = os.getenv("DATABASE_URL", SQLITE_DATABASE_URL)

# Fix for Heroku/Supabase postgres URLs if they start with postgres://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        POSTGRES_ASYNC_URL_PREFIX,
        1,
    )
elif (
    DATABASE_URL
    and DATABASE_URL.startswith("postgresql://")
    and not DATABASE_URL.startswith(POSTGRES_ASYNC_URL_PREFIX)
):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        POSTGRES_ASYNC_URL_PREFIX,
        1,
    )


# Handle sslmode parameter for PostgreSQL connections
def _build_ssl_context_from_mode(mode: str):
    normalized = mode.lower()
    if normalized == "disable":
        return False
    context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_default_certs()
    if normalized == "verify-ca":
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = False
    elif normalized == "verify-full":
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True
    return context


def _parse_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def _parse_float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


connect_args = {}
if DATABASE_URL and "postgresql" in DATABASE_URL:
    base_url = DATABASE_URL
    query_string = ""
    if "?" in DATABASE_URL:
        base_url, _, query_string = DATABASE_URL.partition("?")
    query_params = parse_qs(query_string, keep_blank_values=True)
    ssl_modes = query_params.pop("sslmode", None)
    if query_params:
        DATABASE_URL = f"{base_url}?{urlencode(query_params, doseq=True)}"
    else:
        DATABASE_URL = base_url
    if ssl_modes:
        connect_args["ssl"] = _build_ssl_context_from_mode(ssl_modes[0])

# Security: Ensure sensitive information is not logged
if "password" in DATABASE_URL.lower():
    logger.warning(
        "database URL contains password component",
        action="ensure DSN is redacted in production logs",
    )

is_postgres = "postgresql" in DATABASE_URL
engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
    "connect_args": connect_args,
}

if is_postgres:
    engine_kwargs.update(
        {
            "poolclass": AsyncAdaptedQueuePool,
            "pool_size": _parse_int_env("DATABASE_POOL_SIZE", 5),
            "max_overflow": _parse_int_env("DATABASE_MAX_OVERFLOW", 10),
            "pool_timeout": _parse_float_env("DATABASE_POOL_TIMEOUT", 30.0),
        }
    )

engine = create_async_engine(DATABASE_URL, **engine_kwargs)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Async generator for FastAPI Depends() injection."""
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_readonly_db() -> AsyncGenerator[AsyncSession, None]:
    """Async generator for read-only FastAPI dependencies."""
    session = AsyncSessionLocal()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for use with 'async with' in non-endpoint code."""
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def warmup_pool() -> None:
    """Acquire and release one connection to warm the pool before first request."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def init_db():
    """Initialize database tables"""
    try:
        from .models import Base

        async with engine.begin() as conn:
            # Create tables if they don't exist
            await conn.run_sync(Base.metadata.create_all)
        return True
    except SQLAlchemyError as exc:
        logger.warning(
            "database initialization failed",
            error=str(exc),
            impact=("continuing without database - some features may be limited"),
        )
        return False
