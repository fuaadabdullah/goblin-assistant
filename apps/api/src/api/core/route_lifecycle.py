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


_LEGACY_PREFIXES = (
    "/health",
    "/settings",
    "/providers/models",
    "/chat",
    "/api/chat",
    "/search",
    "/sandbox",
    "/account",
    "/support",
    "/auth",
)

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

_LEGACY_SUNSET = "2026-12-31T00:00:00Z"


def classify_route_lifecycle(path: str) -> LifecycleDecision:
    if path == "/" or path.startswith("/api/v1"):
        return LifecycleDecision(RouteLifecycle.STABLE)

    if path.startswith(_INTERNAL_PREFIXES):
        return LifecycleDecision(RouteLifecycle.INTERNAL)

    if path.startswith(_LEGACY_PREFIXES):
        return LifecycleDecision(RouteLifecycle.LEGACY, sunset_at=_LEGACY_SUNSET)

    if path.startswith(_EXPERIMENTAL_PREFIXES):
        return LifecycleDecision(RouteLifecycle.EXPERIMENTAL)

    return LifecycleDecision(RouteLifecycle.STABLE)
