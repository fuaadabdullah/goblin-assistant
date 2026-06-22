"""Route mounting helpers for api.main."""

from fastapi import FastAPI


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
    )
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(settings_router, prefix="/api/v1")
    app.include_router(providers_models_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(search_router, prefix="/api/v1")
    app.include_router(sandbox_router, prefix="/api/v1")
    app.include_router(account_router, prefix="/api/v1")
    app.include_router(support_router, prefix="/api/v1")
    app.include_router(raptor_router, prefix="/api/v1")
    app.include_router(api_keys_router, prefix="/api/v1")
    app.include_router(privacy_router, prefix="/api/v1")
    app.include_router(routing_router, prefix="/api/v1")
    app.include_router(parse_router, prefix="/api/v1")
    app.include_router(write_time_router, prefix="/api/v1")
    app.include_router(stream_router, prefix="/api/v1")
    app.include_router(ops_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(secrets_router, prefix="/api/v1")
    if semantic_chat_router is not None:
        app.include_router(semantic_chat_router, prefix="/api/v1")
    if model_suggestion_debug_router is not None:
        app.include_router(model_suggestion_debug_router, prefix="/api/v1")
    if observability_debug_router is not None:
        app.include_router(observability_debug_router, prefix="/api/v1")
    if retrieval_metrics_router is not None:
        app.include_router(retrieval_metrics_router, prefix="/api/v1")

    if routing_analytics_available and routing_analytics_router:
        app.include_router(routing_analytics_router, prefix="/api/v1")
