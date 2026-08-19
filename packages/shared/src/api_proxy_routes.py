"""Canonical frontend proxy-route contract shared by web and tooling."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProxyPrefixSpec:
    """Wildcard prefix proxy: any sub-path under frontend_prefix is forwarded.

    Validation requires at least one manifest route that starts with backend_prefix.
    Use this when the backend implements a whole subtree (e.g. /api/v1/chat/**).
    """

    frontend_prefix: str
    backend_prefix: str


@dataclass(frozen=True)
class ProxyEndpointSpec:
    """Point-to-point endpoint proxy: frontend_path maps to exactly backend_path.

    Validation requires an exact path match in the manifest — no prefix or
    startswith logic.  Use this when the backend implements a single endpoint
    (e.g. /api/v1/providers/models) rather than a whole subtree.
    """

    frontend_path: str
    backend_path: str


# Backward-compatible alias — any tooling that references ProxyRouteSpec still works.
ProxyRouteSpec = ProxyPrefixSpec


PROXY_PREFIX_ROUTES: tuple[ProxyPrefixSpec, ...] = (
    ProxyPrefixSpec("/api/account", "/api/v1/account"),
    ProxyPrefixSpec("/api/agent", "/api/v1/agent"),
    ProxyPrefixSpec("/api/auth", "/api/v1/auth"),
    ProxyPrefixSpec("/api/chat", "/api/v1/chat"),
    ProxyPrefixSpec("/api/costs", "/api/v1/routing/costs"),
    ProxyPrefixSpec("/api/feedback", "/api/v1/api/feedback"),
    ProxyPrefixSpec("/api/health/routing", "/api/v1/health/routing"),
    ProxyPrefixSpec("/api/health/streaming", "/api/v1/health/streaming"),
    ProxyPrefixSpec("/api/metrics", "/metrics"),
    ProxyPrefixSpec("/api/raptor", "/api/v1/raptor"),
    ProxyPrefixSpec("/api/routing", "/api/v1/routing"),
    ProxyPrefixSpec("/api/runtime", "/api/v1/api"),
    ProxyPrefixSpec("/api/sandbox", "/api/v1/sandbox"),
    ProxyPrefixSpec("/api/search", "/api/v1/search"),
    ProxyPrefixSpec("/api/settings", "/api/v1/settings"),
    ProxyPrefixSpec("/api/support", "/api/v1/support"),
)

PROXY_ENDPOINT_ROUTES: tuple[ProxyEndpointSpec, ...] = (
    # /api/v1/providers is not a root endpoint — only /models exists under it.
    # ProxyPrefixSpec would have accepted /api/v1/providers (falsely) because
    # _matches_prefix("/api/v1/providers/models", "/api/v1/providers") == True.
    # ProxyEndpointSpec enforces an exact manifest match, preventing that bug.
    ProxyEndpointSpec("/api/providers/models", "/api/v1/providers/models"),
)

# Backward-compatible alias — tooling/quality/api_path_validation.py reads PROXY_ROUTES.
PROXY_ROUTES = PROXY_PREFIX_ROUTES

EXPLICIT_FRONTEND_PATHS: tuple[str, ...] = (
    "/api/debug/model-usage",
    "/api/errors",
    "/api/generate",
    "/api/health",
    "/api/models",
    "/api/system-status",
)
