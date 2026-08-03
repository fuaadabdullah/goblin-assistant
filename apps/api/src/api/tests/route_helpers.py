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
    """Yield a RouteView for every APIRoute reachable from *routes*.

    Handles three FastAPI/Starlette layouts:
    A) Flat: include_router stores APIRoute objects directly with full paths.
    B) _IncludedRouter (FastAPI 0.141+/Starlette 0.49): wrapper with
       .original_router (sub-router) and .include_context.prefix (prefix).
    C) Starlette Mount: .path carries the prefix, .routes the sub-routes.
    """
    for route in routes:
        if isinstance(route, APIRoute):
            yield RouteView(
                path=_join_route_path(prefix, route.path),
                methods=frozenset(route.methods or ()),
                endpoint=route.endpoint,
            )
            continue

        # Layout B: _IncludedRouter (FastAPI 0.141+/Starlette 0.49)
        include_context = getattr(route, "include_context", None)
        if include_context is not None:
            route_prefix = getattr(include_context, "prefix", "") or ""
            sub_router = getattr(route, "original_router", None) or getattr(
                include_context, "included_router", None
            )
        else:
            # Layout C: Mount (.path + .routes) or older .router + .prefix
            sub_router = getattr(route, "router", None)
            route_prefix = (
                getattr(route, "prefix", None) or getattr(route, "path", None) or ""
            )
            if sub_router is None:
                sub_router = route  # Mount: .routes lives on route itself

        if sub_router is None:
            continue
        included_routes = getattr(sub_router, "routes", None)
        if included_routes is None:
            continue

        yield from iter_route_views(
            included_routes,
            prefix=_join_route_path(prefix, route_prefix),
        )
