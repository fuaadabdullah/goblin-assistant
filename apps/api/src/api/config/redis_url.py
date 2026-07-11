"""Canonical Redis URL validation for runtime clients."""

from __future__ import annotations

from urllib.parse import urlsplit

import structlog

DEFAULT_REDIS_URL = "redis://localhost:6379/0"
SUPPORTED_REDIS_SCHEMES = frozenset({"redis", "rediss", "unix"})


def resolve_redis_url(
    redis_url: str | None,
    *,
    component: str,
    default: str = DEFAULT_REDIS_URL,
) -> str:
    """Return a supported Redis URL without exposing URL contents in logs."""

    candidate = (redis_url or default).strip()
    scheme = urlsplit(candidate).scheme.lower()
    if scheme in SUPPORTED_REDIS_SCHEMES:
        return candidate

    structlog.get_logger().warning(
        "redis_url_invalid",
        component=component,
        configured_scheme=scheme or "missing",
        fallback_scheme=urlsplit(default).scheme,
    )
    return default
