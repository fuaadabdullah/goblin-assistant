"""Route mounting helpers for api.main."""

from fastapi import FastAPI


def mount_primary_routes(
    app: FastAPI,
    *,
    api_router,
    auth_router,
    routing_router,
    parse_router,
    raptor_router,
    api_keys_router,
    settings_router,
    search_router,
    stream_router,
    chat_router,
    semantic_chat_router,
    write_time_router,
    health_router,
    ops_router,
    secrets_router,
    privacy_router,
    model_suggestion_debug_router,
    observability_debug_router,
    retrieval_metrics_router,
    sandbox_router,
    providers_models_router,
    account_router,
    support_router,
    routing_analytics_available: bool,
    routing_analytics_router,
) -> None:
    _ = (
        api_router,
        auth_router,
        raptor_router,
        api_keys_router,
        settings_router,
        search_router,
        chat_router,
        health_router,
        privacy_router,
        sandbox_router,
        providers_models_router,
        account_router,
        support_router,
    )
    # Non-versioned routes that are intentionally internal/experimental.
    app.include_router(routing_router)
    app.include_router(parse_router)
    app.include_router(stream_router)
    app.include_router(semantic_chat_router)
    app.include_router(write_time_router)
    app.include_router(ops_router)
    app.include_router(secrets_router)
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
        secrets_router,
    )
    app.include_router(health_router, prefix="/v1")
    app.include_router(settings_router, prefix="/v1")
    app.include_router(providers_models_router, prefix="/v1")
    app.include_router(chat_router, prefix="/v1")
    app.include_router(api_router, prefix="/v1")
    app.include_router(auth_router, prefix="/v1")
    app.include_router(search_router, prefix="/v1")
    app.include_router(sandbox_router, prefix="/v1")
    app.include_router(account_router, prefix="/v1")
    app.include_router(support_router, prefix="/v1")
    app.include_router(raptor_router, prefix="/v1")
    app.include_router(api_keys_router, prefix="/v1")
    app.include_router(privacy_router, prefix="/v1")
    app.include_router(routing_router, prefix="/v1")
    app.include_router(parse_router, prefix="/v1")
    app.include_router(write_time_router, prefix="/v1")
    app.include_router(stream_router, prefix="/v1")
    app.include_router(ops_router, prefix="/v1")
    app.include_router(secrets_router, prefix="/v1")
