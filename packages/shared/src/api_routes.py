"""Canonical API route prefix contract shared by backend and generators."""

from __future__ import annotations

API_PREFIX = "/api"
API_VERSION = "v1"
API_V1_PREFIX = f"{API_PREFIX}/{API_VERSION}"

ROUTE_PREFIXES: dict[str, str] = {
    "chat": f"{API_V1_PREFIX}/chat",
    "auth": f"{API_V1_PREFIX}/auth",
    "providers": f"{API_V1_PREFIX}/providers",
    "health": f"{API_V1_PREFIX}/health",
    "settings": f"{API_V1_PREFIX}/settings",
}

V1_CHAT_PREFIX = ROUTE_PREFIXES["chat"]
V1_AUTH_PREFIX = ROUTE_PREFIXES["auth"]
V1_PROVIDERS_PREFIX = ROUTE_PREFIXES["providers"]
V1_HEALTH_PREFIX = ROUTE_PREFIXES["health"]
V1_SETTINGS_PREFIX = ROUTE_PREFIXES["settings"]


def build_versioned_path(*segments: str) -> str:
    cleaned = [segment.strip("/") for segment in segments if segment and segment.strip("/")]
    if not cleaned:
        return API_V1_PREFIX
    return f"{API_V1_PREFIX}/{'/'.join(cleaned)}"
