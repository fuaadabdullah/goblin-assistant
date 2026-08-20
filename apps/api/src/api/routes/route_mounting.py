"""Route mounting helpers for api.main."""

from fastapi import FastAPI

from ..nodes.router import router as nodes_router
from ..shared_api_routes_runtime import API_V1_PREFIX


def mount_versioned_primary_routes(
    app: FastAPI,
    *,
    health_router,
    settings_router,
    providers_models_router,
    chat_router,
    api_router,
    auth_router,
    search_router,
    sandbox_router,
    account_router,
    support_router,
    feature_flags_router,
    notifications_router,
    agent_router,
    raptor_router,
    api_keys_router,
    privacy_router,
    routing_router,
    parse_router,
    write_time_router,
    stream_router,
    ops_router,
    admin_router,
    secrets_router,
    semantic_chat_router=None,
    model_suggestion_debug_router=None,
    observability_debug_router=None,
    retrieval_metrics_router=None,
    prometheus_router=None,
    routing_analytics_available: bool = False,
    routing_analytics_router=None,
) -> None:
    _ = (
        health_router,
        settings_router,
        providers_models_router,
        chat_router,
        api_router,
        auth_router,
        search_router,
        sandbox_router,
        account_router,
        support_router,
        feature_flags_router,
        notifications_router,
        agent_router,
        raptor_router,
        api_keys_router,
        privacy_router,
        routing_router,
        parse_router,
        write_time_router,
        stream_router,
        ops_router,
        admin_router,
        secrets_router,
        semantic_chat_router,
        model_suggestion_debug_router,
        observability_debug_router,
        retrieval_metrics_router,
        prometheus_router,
    )
    app.include_router(health_router, prefix=API_V1_PREFIX)
    app.include_router(settings_router, prefix=API_V1_PREFIX)
    app.include_router(providers_models_router, prefix=API_V1_PREFIX)
    app.include_router(chat_router, prefix=API_V1_PREFIX)
    app.include_router(api_router, prefix=API_V1_PREFIX)
    app.include_router(auth_router, prefix=API_V1_PREFIX)
    app.include_router(search_router, prefix=API_V1_PREFIX)
    app.include_router(sandbox_router, prefix=API_V1_PREFIX)
    app.include_router(account_router, prefix=API_V1_PREFIX)
    app.include_router(support_router, prefix=API_V1_PREFIX)
    app.include_router(feature_flags_router, prefix=API_V1_PREFIX)
    app.include_router(notifications_router, prefix=API_V1_PREFIX)
    app.include_router(agent_router, prefix=API_V1_PREFIX)
    app.include_router(raptor_router, prefix=API_V1_PREFIX)
    app.include_router(api_keys_router, prefix=API_V1_PREFIX)
    app.include_router(privacy_router, prefix=API_V1_PREFIX)
    app.include_router(routing_router, prefix=API_V1_PREFIX)
    app.include_router(parse_router, prefix=API_V1_PREFIX)
    app.include_router(write_time_router, prefix=API_V1_PREFIX)
    app.include_router(stream_router, prefix=API_V1_PREFIX)
    app.include_router(ops_router, prefix=API_V1_PREFIX)
    app.include_router(admin_router, prefix=API_V1_PREFIX)
    app.include_router(secrets_router, prefix=API_V1_PREFIX)
    # Self-hosted compute nodes. Composed here rather than threaded through
    # register_routes: it is a static internal router with no construction
    # options, unlike the conditionally-built routers above.
    app.include_router(nodes_router, prefix=API_V1_PREFIX)
    if semantic_chat_router is not None:
        app.include_router(semantic_chat_router, prefix=API_V1_PREFIX)
    if model_suggestion_debug_router is not None:
        app.include_router(model_suggestion_debug_router, prefix=API_V1_PREFIX)
    if observability_debug_router is not None:
        app.include_router(observability_debug_router, prefix=API_V1_PREFIX)
    if retrieval_metrics_router is not None:
        app.include_router(retrieval_metrics_router, prefix=API_V1_PREFIX)
    if prometheus_router is not None:
        app.include_router(prometheus_router)

    if routing_analytics_available and routing_analytics_router:
        app.include_router(routing_analytics_router, prefix=API_V1_PREFIX)
