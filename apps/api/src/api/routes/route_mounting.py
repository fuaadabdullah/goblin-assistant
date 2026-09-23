"""Route mounting helpers for api.main."""

from collections.abc import Iterable, Iterator
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute

from ..shared_api_routes_runtime import API_V1_PREFIX


def iter_effective_routes(app: FastAPI) -> Iterator[Any]:
    """Yield the app's API routes carrying their final, prefixed paths.

    FastAPI includes sub-routers lazily: ``app.routes`` holds internal
    wrapper objects rather than the flattened ``APIRoute`` instances, so
    walking it directly sees only the handful of routes declared on the app
    itself -- ``/``, ``/test`` and the docs endpoints -- and none of the
    mounted routers. The wrappers can materialise their routes with the
    prefixes applied, and they nest, because routers include routers, so
    this has to recurse.

    Routes are yielded as objects exposing ``path``, ``methods`` and the
    other attributes ``APIRoute`` provides. Older FastAPI versions flatten
    into ``app.routes`` and are handled by the ``APIRoute`` branch.
    """
    yield from _expand(getattr(app, "routes", ()))


def _expand(routes: Iterable[Any]) -> Iterator[Any]:
    for route in routes:
        materialize = getattr(route, "effective_candidates", None)
        if callable(materialize):
            yield from _expand(materialize())
            continue

        # APIRoute on older FastAPI; on newer ones the materialised context,
        # which carries the same fields plus its final prefixed path.
        if isinstance(route, APIRoute) or hasattr(route, "from_api_route"):
            yield route


def effective_route_paths(app: FastAPI) -> set[str]:
    """Convenience wrapper: the set of paths the app actually serves."""
    return {path for path in (getattr(r, "path", "") for r in iter_effective_routes(app)) if path}


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
