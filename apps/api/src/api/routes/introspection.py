"""Enumerate the APIRoutes an app actually serves, across FastAPI versions.

FastAPI >= 0.141 keeps included routers nested (``_IncludedRouter``) instead
of flattening them into ``app.routes``, so ``app.routes`` no longer lists the
mounted endpoints. Anything that inspects the route table (tests, contract
exporters) should go through ``iter_api_routes`` instead.
"""

from __future__ import annotations

from typing import Any, List

from fastapi import routing as fastapi_routing
from fastapi.routing import APIRoute


class MountedRoute:
    """An APIRoute seen through its include context.

    ``path`` is the full mounted path (router prefixes applied). Other
    attributes resolve against the effective route first -- which carries what
    the include merged in, such as router-level ``tags`` or
    ``include_in_schema`` -- and then the underlying APIRoute (``endpoint``,
    ``methods``, ``name`` ...).
    """

    def __init__(self, route: APIRoute, path: str, effective: Any = None) -> None:
        self.route = route
        self.path = path
        self._effective = effective

    def __getattr__(self, name: str) -> Any:
        effective = self.__dict__.get("_effective")
        if effective is not None and hasattr(effective, name):
            return getattr(effective, name)
        return getattr(self.route, name)

    def __repr__(self) -> str:
        return "MountedRoute(path={!r}, methods={!r})".format(self.path, self.route.methods)


def iter_api_routes(app: Any) -> List[MountedRoute]:
    """Every APIRoute reachable from ``app``, with its effective path."""
    iter_route_contexts = getattr(fastapi_routing, "iter_route_contexts", None)
    if iter_route_contexts is None:  # FastAPI < 0.141 flattens on include.
        return [MountedRoute(r, r.path) for r in app.routes if isinstance(r, APIRoute)]

    routes: List[MountedRoute] = []
    for context in iter_route_contexts(app.routes):
        route = getattr(context, "route", None)
        if isinstance(route, APIRoute):
            # _route_context is the merged per-include view. It is private, so
            # degrade to the bare route if a later release renames it.
            effective = getattr(context, "_route_context", None)
            routes.append(MountedRoute(route, getattr(context, "path", route.path), effective))
    return routes
