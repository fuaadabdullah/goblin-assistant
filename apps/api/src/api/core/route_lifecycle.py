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


_LEGACY_PREFIXES: tuple[str, ...] = ()

_INTERNAL_PREFIXES = (
    "/docs",
    "/openapi.json",
    "/redoc",
    "/debug",
    "/ops",
    "/secrets",
    "/test",
)

_EXPERIMENTAL_PREFIXES = (
    "/parse",
    "/routing",
    "/write-time",
    "/semantic-chat",
    "/stream",
)


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

    if normalized_path.startswith(_LEGACY_PREFIXES):
        return LifecycleDecision(RouteLifecycle.LEGACY)

    if normalized_path.startswith(_EXPERIMENTAL_PREFIXES):
        return LifecycleDecision(RouteLifecycle.EXPERIMENTAL)

    return LifecycleDecision(RouteLifecycle.STABLE)
