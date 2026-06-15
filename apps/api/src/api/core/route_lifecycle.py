from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RouteLifecycle(str, Enum):
    STABLE = "stable"
    LEGACY = "legacy"
    EXPERIMENTAL = "experimental"
    INTERNAL = "internal"


@dataclass(frozen=True)
class LifecycleDecision:
    lifecycle: RouteLifecycle
    sunset_at: Optional[str] = None


_LEGACY_PREFIXES: dict[str, str] = {
    "/api": "2026-09-15",
    "/auth": "2026-09-15",
    "/chat": "2026-09-15",
    "/health": "2026-09-15",
    "/routing": "2026-09-15",
    "/parse": "2026-09-15",
    "/search": "2026-09-15",
    "/stream": "2026-09-15",
    "/write-time": "2026-09-15",
    "/sandbox": "2026-09-15",
    "/raptor": "2026-09-15",
    "/api-keys": "2026-09-15",
    "/admin": "2026-09-15",
    "/semantic-chat": "2026-09-15",
}

_INTERNAL_PREFIXES = (
    "/docs",
    "/openapi.json",
    "/redoc",
    "/debug",
    "/ops",
    "/secrets",
    "/test",
)

_EXPERIMENTAL_PREFIXES = ()


def _strip_version_prefix(path: str) -> str:
    if path == "/api/v1":
        return "/"
    if path.startswith("/api/v1/"):
        stripped = path[len("/api/v1") :]
        return stripped if stripped else "/"
    return path


def classify_route_lifecycle(path: str) -> LifecycleDecision:
    normalized_path = _strip_version_prefix(path)

    if normalized_path == "/":
        return LifecycleDecision(RouteLifecycle.STABLE)

    if normalized_path.startswith(_INTERNAL_PREFIXES):
        return LifecycleDecision(RouteLifecycle.INTERNAL)

    for prefix, sunset_at in _LEGACY_PREFIXES.items():
        if normalized_path.startswith(prefix):
            return LifecycleDecision(RouteLifecycle.LEGACY, sunset_at=sunset_at)

    if normalized_path.startswith(_EXPERIMENTAL_PREFIXES):
        return LifecycleDecision(RouteLifecycle.EXPERIMENTAL)

    return LifecycleDecision(RouteLifecycle.STABLE)
