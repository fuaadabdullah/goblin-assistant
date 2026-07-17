#!/usr/bin/env python3
"""Generate shared TypeScript route path types from the checked-in route manifest."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "packages" / "sdk" / "openapi" / "routes.json"
OUTPUT_PATH = REPO_ROOT / "packages" / "shared" / "src" / "generated" / "api-route-paths.ts"


def _load_paths() -> list[str]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    routes = manifest.get("routes", [])
    if not isinstance(routes, list):
        return []

    unique_paths: list[str] = []
    seen: set[str] = set()
    for route in routes:
        if not isinstance(route, dict):
            continue
        if not route.get("include_in_schema", True):
            continue
        path = route.get("path")
        if isinstance(path, str) and path and path not in seen:
            seen.add(path)
            unique_paths.append(path)
    return sorted(unique_paths)


def _render(paths: list[str]) -> str:
    lines = [
        "/**",
        " * Generated from packages/sdk/openapi/routes.json.",
        " * Do not edit by hand.",
        " */",
        "",
        "export const API_ROUTE_PATHS = [",
    ]
    lines.extend(f"  '{path}'," for path in paths)
    lines.extend(
        [
            "] as const;",
            "",
            "export type ApiRoutePath = typeof API_ROUTE_PATHS[number];",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    paths = _load_paths()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(_render(paths), encoding="utf-8")
    print(f"Generated {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
