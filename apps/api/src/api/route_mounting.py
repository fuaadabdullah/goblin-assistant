"""Route mounting helpers for api.main."""

from fastapi import FastAPI


def mount_primary_routes(
    app: FastAPI,
    *,
    api_router,
    auth_router,
    routing_router,
    parse_router,
    search_router,
    stream_router,
    chat_router,
    write_time_router,
    health_router,
    ops_router,
    admin_router,
    secrets_router,
    sandbox_router,
    semantic_chat_router,
    model_suggestion_debug_router,
    observability_debug_router,
    retrieval_metrics_router,
    routing_analytics_available: bool,
    routing_analytics_router,
) -> None:
    # Preserve legacy root-level public aliases while keeping /api/v1 canonical.
    app.include_router(api_router)
    app.include_router(auth_router)
    app.include_router(routing_router)
    app.include_router(parse_router)
    app.include_router(search_router)
    app.include_router(stream_router)
    app.include_router(chat_router)
    app.include_router(write_time_router)
    app.include_router(health_router)
    app.include_router(ops_router)
    app.include_router(admin_router)
    app.include_router(secrets_router)
    app.include_router(sandbox_router)

    # Internal/experimental routes with no /api/v1 equivalent.
    app.include_router(semantic_chat_router)
    app.include_router(model_suggestion_debug_router)
    app.include_router(observability_debug_router)
    app.include_router(retrieval_metrics_router)

    if routing_analytics_available and routing_analytics_router:
        app.include_router(routing_analytics_router)


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
