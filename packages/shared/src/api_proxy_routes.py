"""Canonical frontend proxy-route contract shared by web and tooling."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProxyRouteSpec:
    frontend_prefix: str
    backend_prefix: str


PROXY_ROUTES: tuple[ProxyRouteSpec, ...] = (
    ProxyRouteSpec("/api/account", "/api/v1/account"),
    ProxyRouteSpec("/api/agent", "/api/v1/agent"),
    ProxyRouteSpec("/api/auth", "/api/v1/auth"),
    ProxyRouteSpec("/api/chat", "/api/v1/chat"),
    ProxyRouteSpec("/api/costs", "/api/v1/routing/costs"),
    ProxyRouteSpec("/api/feedback", "/api/v1/api/feedback"),
    ProxyRouteSpec("/api/health/routing", "/api/v1/health/routing"),
    ProxyRouteSpec("/api/health/streaming", "/api/v1/health/streaming"),
    ProxyRouteSpec("/api/metrics", "/metrics"),
    ProxyRouteSpec("/api/providers", "/api/v1/providers"),
    ProxyRouteSpec("/api/raptor", "/api/v1/raptor"),
    ProxyRouteSpec("/api/routing", "/api/v1/routing"),
    ProxyRouteSpec("/api/runtime", "/api/v1/api"),
    ProxyRouteSpec("/api/sandbox", "/api/v1/sandbox"),
    ProxyRouteSpec("/api/search", "/api/v1/search"),
    ProxyRouteSpec("/api/settings", "/api/v1/settings"),
    ProxyRouteSpec("/api/support", "/api/v1/support"),
)


EXPLICIT_FRONTEND_PATHS: tuple[str, ...] = (
    "/api/debug/model-usage",
    "/api/errors",
    "/api/generate",
    "/api/health",
    "/api/models",
    "/api/system-status",
)
