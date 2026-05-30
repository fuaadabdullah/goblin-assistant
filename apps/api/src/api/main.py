#!/usr/bin/env python3
"""FastAPI compatibility entrypoint for Goblin Assistant."""

from contextlib import asynccontextmanager

from .app_factory import create_app
from .artifact_cleanup import artifact_cleanup_service
from .lifespan import lifespan as _lifespan_impl
from .monitoring import monitor
from .secrets_router import cleanup_secrets_adapter, init_secrets_adapter
from .storage.cache import cache
from .storage.database import init_db


@asynccontextmanager
async def lifespan(app):
    # Keep api.main patch points functional for existing tests/callers.
    from . import lifespan as lifespan_module

    lifespan_module.cache = cache
    lifespan_module.init_db = init_db
    lifespan_module.monitor = monitor
    lifespan_module.init_secrets_adapter = init_secrets_adapter
    lifespan_module.cleanup_secrets_adapter = cleanup_secrets_adapter
    lifespan_module.artifact_cleanup_service = artifact_cleanup_service
    async with _lifespan_impl(app):
        yield

app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
