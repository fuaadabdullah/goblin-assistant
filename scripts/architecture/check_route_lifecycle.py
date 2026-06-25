#!/usr/bin/env python3
"""Validate route lifecycle classifications for API endpoints."""

from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
API_SRC_ROOT = REPO_ROOT / "apps" / "api" / "src"
if str(API_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(API_SRC_ROOT))

# auth/router/config.py raises at import time without JWT_SECRET_KEY;
# set a dummy so the app can register routes for inspection without fully booting.
os.environ.setdefault("JWT_SECRET_KEY", "check-route-lifecycle-dummy-secret")

from api.core.route_lifecycle import RouteLifecycle, classify_route_lifecycle  # noqa: E402
from api.main import app  # noqa: E402


def main() -> int:
    violations: list[str] = []
    lifecycle_counts = {
        RouteLifecycle.STABLE: 0,
        RouteLifecycle.LEGACY: 0,
        RouteLifecycle.EXPERIMENTAL: 0,
        RouteLifecycle.INTERNAL: 0,
    }

    for route in app.routes:
        path = getattr(route, "path", "")
        methods = sorted(
            method
            for method in getattr(route, "methods", set())
            if method not in {"HEAD", "OPTIONS"}
        )
        if not path or not methods:
            continue

        decision = classify_route_lifecycle(path)
        lifecycle_counts[decision.lifecycle] += 1

        if decision.lifecycle is RouteLifecycle.LEGACY and not decision.sunset_at:
            violations.append(f"{path}: legacy route missing sunset_at")
        if (
            decision.lifecycle is RouteLifecycle.STABLE
            and path.startswith("/api/v1")
            and decision.sunset_at
        ):
            violations.append(f"{path}: stable /api/v1 route cannot carry sunset_at")

    if violations:
        print("Route lifecycle check failed:")
        for violation in violations:
            print(f"  - {violation}")
        return 1

    print(
        "Route lifecycle check passed "
        f"(stable={lifecycle_counts[RouteLifecycle.STABLE]}, "
        f"legacy={lifecycle_counts[RouteLifecycle.LEGACY]}, "
        f"experimental={lifecycle_counts[RouteLifecycle.EXPERIMENTAL]}, "
        f"internal={lifecycle_counts[RouteLifecycle.INTERNAL]})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
