import asyncio
import os
import ssl
import sys
from logging.config import fileConfig
from urllib.parse import parse_qs, urlencode

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Add the current directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import the Base and models
from api.storage.models import Base
from api.storage.models import UserModel, ConversationModel, MessageModel

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url():
    """Get database URL from environment, normalised for asyncpg."""
    url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./goblin_assistant.db")

    # Rewrite sync Heroku/Supabase URLs to asyncpg dialect
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return url


def _ssl_connect_args(url: str) -> dict:
    """Extract sslmode from the URL query string and return asyncpg connect_args."""
    if "postgresql" not in url or "?" not in url:
        return {}

    base, _, qs = url.partition("?")
    params = parse_qs(qs, keep_blank_values=True)
    modes = params.pop("sslmode", None)
    if not modes:
        return {}

    mode = modes[0].lower()
    if mode == "disable":
        return {"ssl": False}

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    if mode in ("verify-ca", "verify-full"):
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.check_hostname = mode == "verify-full"
    return {"ssl": ctx}


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    url = get_url()
    connect_args = _ssl_connect_args(url)
    # Strip sslmode from URL query string — asyncpg uses connect_args instead
    if "sslmode=" in url:
        base, _, qs = url.partition("?")
        params = parse_qs(qs, keep_blank_values=True)
        params.pop("sslmode", None)
        url = f"{base}?{urlencode(params, doseq=True)}" if params else base

    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
