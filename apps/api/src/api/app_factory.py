import os

from fastapi import FastAPI

from ._version import get_version
from .admin_routes import router as admin_router
from .api_router import router as api_router
from .auth.router import router as auth_router
from .bootstrap.middleware import (
    add_contract_lifecycle_headers,
    install_runtime_middlewares,
)
from .bootstrap.routes import register_routes
from .bootstrap.startup import (
    init_ddtrace,
    init_otel,
    init_sentry,
    load_env_files,
    resolve_optional_routing_analytics_router,
)
from .chat_router import router as chat_router
from .exception_handlers import register_exception_handlers
from .health import router as health_router
from .lifespan import lifespan
from .observability.debug_router import router as observability_debug_router
from .observability.metrics_router import router as retrieval_metrics_router
from .observability.prometheus_router import router as prometheus_router
from .observability.telemetry import instrument_fastapi_app
from .routes.account_router import router as account_router
from .routes.agent import router as agent_router
from .routes.api_keys_router import router as api_keys_router
from .routes.debug import router as model_suggestion_debug_router
from .routes.feature_flags_router import router as feature_flags_router
from .routes.notifications_router import router as notifications_router
from .routes.ops_router import router as ops_router
from .routes.parse_router import router as parse_router
from .routes.privacy import router as privacy_router
from .routes.providers_models import router as providers_models_router
from .routes.raptor_router import router as raptor_router
from .routes.routing_router import router as routing_router
from .routes.search_router import router as search_router
from .routes.secrets_router import router as secrets_router
from .routes.semantic_chat_router import router as semantic_chat_router
from .routes.settings_router import router as settings_router
from .routes.stream_router import router as stream_router
from .routes.support_router import router as support_router
from .routes.write_time_router import router as write_time_router
from .sandbox_api import router as sandbox_router


def create_app() -> FastAPI:
    load_env_files()
    init_sentry()
    init_otel()
    init_ddtrace()
    routing_analytics_available, routing_analytics_router = (
        resolve_optional_routing_analytics_router()
    )

    app = FastAPI(
        title="Goblin Assistant API",
        description="AI-powered development assistant with multi-provider routing",
        version=get_version(),
        lifespan=lifespan,
    )
    instrument_fastapi_app(app)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "message": "Goblin Assistant API",
            "version": get_version(),
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/test")
    async def test() -> dict[str, str]:
        return {"status": "ok"}

    app.middleware("http")(add_contract_lifecycle_headers)
    register_exception_handlers(app)

    environment = os.getenv("ENVIRONMENT", "development").lower()
    install_runtime_middlewares(app, environment=environment)

    register_routes(
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
        admin_router=admin_router,
        secrets_router=secrets_router,
        privacy_router=privacy_router,
        model_suggestion_debug_router=model_suggestion_debug_router,
        observability_debug_router=observability_debug_router,
        retrieval_metrics_router=retrieval_metrics_router,
        prometheus_router=prometheus_router,
        sandbox_router=sandbox_router,
        providers_models_router=providers_models_router,
        account_router=account_router,
        support_router=support_router,
        feature_flags_router=feature_flags_router,
        notifications_router=notifications_router,
        agent_router=agent_router,
        routing_analytics_available=routing_analytics_available,
        routing_analytics_router=routing_analytics_router,
    )

    return app
