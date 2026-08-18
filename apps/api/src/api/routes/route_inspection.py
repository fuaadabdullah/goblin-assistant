"""Compatibility helpers for inspecting mounted FastAPI routes."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any


def iter_effective_routes(routes: Iterable[Any]) -> Iterator[Any]:
    """Yield route-like objects after expanding FastAPI's lazy included routers."""
    for route in routes:
        if isinstance(getattr(route, "path", None), str) and hasattr(route, "methods"):
            yield route
            continue

        effective_contexts = getattr(route, "effective_route_contexts", None)
        if callable(effective_contexts):
            yield from iter_effective_routes(effective_contexts())


def effective_route_paths(routes: Iterable[Any]) -> set[str]:
    return {
        path
        for route in iter_effective_routes(routes)
        if isinstance((path := getattr(route, "path", None)), str)
    }
