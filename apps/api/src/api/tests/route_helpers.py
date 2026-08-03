from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from fastapi.routing import APIRoute


@dataclass(frozen=True)
class RouteView:
    path: str
    methods: frozenset[str]
    endpoint: Any


def _join_route_path(prefix: str, path: str) -> str:
    if not prefix:
        return path or "/"
    if not path:
        return prefix
    return f"{prefix.rstrip('/')}/{path.lstrip('/')}"


def iter_route_views(routes: Iterable[object], *, prefix: str = "") -> Iterator[RouteView]:
    for route in routes:
        if isinstance(route, APIRoute):
            yield RouteView(
                path=_join_route_path(prefix, route.path),
                methods=frozenset(route.methods or ()),
                endpoint=route.endpoint,
            )
            continue

        # FastAPI 0.111+/Starlette 0.49+ wraps included routers as _IncludedRouter
        # which exposes the sub-router via .router and the prefix via .prefix.
        # Older patterns used include_context/original_router; try both.
        sub_router = getattr(route, "router", None)
        route_prefix = getattr(route, "prefix", "")
        if sub_router is None:
            include_context = getattr(route, "include_context", None)
            sub_router = getattr(route, "original_router", None) or getattr(
                include_context, "included_router", None
            )
            route_prefix = getattr(include_context, "prefix", "") if include_context else ""

        included_routes = getattr(sub_router, "routes", None)
        if included_routes is None:
            continue

        yield from iter_route_views(
            included_routes,
            prefix=_join_route_path(prefix, route_prefix),
        )
