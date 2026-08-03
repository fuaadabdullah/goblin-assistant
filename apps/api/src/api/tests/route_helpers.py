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

        # Handle _IncludedRouter (FastAPI 0.111+/Starlette 0.49+) and Starlette Mount.
        # _IncludedRouter stores the sub-router via .router and the prefix via .prefix
        # or .path depending on the version. Mount stores sub-routes in .routes with
        # the prefix in .path. Prefer .prefix (set by include_router); fall back to
        # .path (Mount) then empty string.
        route_prefix = getattr(route, "prefix", None) or getattr(route, "path", None) or ""
        sub_router = getattr(route, "router", route)
        included_routes = getattr(sub_router, "routes", None)
        if included_routes is None:
            continue

        yield from iter_route_views(
            included_routes,
            prefix=_join_route_path(prefix, route_prefix),
        )
