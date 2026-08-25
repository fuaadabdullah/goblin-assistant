from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from fastapi.routing import APIRoute


def iter_effective_routes(routes: Iterable[Any]) -> Iterable[Any]:
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
            continue

        effective_candidates = getattr(route, "effective_candidates", None)
        if callable(effective_candidates):
            yield from iter_effective_routes(effective_candidates())
            continue

        original_route = getattr(route, "original_route", None)
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if isinstance(original_route, APIRoute) and isinstance(path, str) and methods:
            yield route
