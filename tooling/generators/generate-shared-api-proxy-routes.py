#!/usr/bin/env python3
"""Generate shared TypeScript proxy-route contracts from the shared Python contract."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "packages" / "shared" / "src" / "api_proxy_routes.py"
MANIFEST_PATH = REPO_ROOT / "packages" / "sdk" / "openapi" / "routes.json"
OPENAPI_PATH = REPO_ROOT / "packages" / "sdk" / "openapi" / "openapi.json"
OUTPUT_PATH = REPO_ROOT / "packages" / "shared" / "src" / "generated" / "api-proxy-routes.ts"


def _load_contract():
    spec = importlib.util.spec_from_file_location("api_proxy_routes_contract", CONTRACT_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load API proxy route contract: {CONTRACT_PATH}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _normalize_path(path: str) -> str:
    return path.rstrip("/") if path != "/" else "/"


def _collect_paths(value: object) -> list[str]:
    if isinstance(value, str) and value:
        return [_normalize_path(value)]
    if isinstance(value, list):
        return [_normalize_path(item) for item in value if isinstance(item, str) and item]
    return []


def _load_manifest_paths() -> list[str]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    routes = manifest.get("routes", [])
    if not isinstance(routes, list):
        return []

    paths: list[str] = []
    for route in routes:
        if not isinstance(route, dict):
            continue
        for field in (
            "path",
            "canonical_path",
            "replacement_path",
            "compatibility_aliases",
        ):
            paths.extend(_collect_paths(route.get(field)))
    return paths


def _load_openapi_paths() -> list[str]:
    schema = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    paths = schema.get("paths", {})
    if not isinstance(paths, dict):
        return []
    return [_normalize_path(path) for path in paths if isinstance(path, str) and path]


def _load_available_paths() -> list[str]:
    seen: set[str] = set()
    ordered_paths: list[str] = []
    for path in [*_load_manifest_paths(), *_load_openapi_paths()]:
        if path in seen:
            continue
        seen.add(path)
        ordered_paths.append(path)
    return ordered_paths


def _matches_prefix(path: str, prefix: str) -> bool:
    normalized_path = _normalize_path(path)
    normalized_prefix = _normalize_path(prefix)
    return normalized_path == normalized_prefix or normalized_path.startswith(f"{normalized_prefix}/")


def _validate_backend_targets(module, manifest_paths: list[str]) -> None:
    for route in module.PROXY_ROUTES:
        backend_prefix = route.backend_prefix.rstrip("/") if route.backend_prefix != "/" else "/"
        if not any(_matches_prefix(path, backend_prefix) for path in manifest_paths):
            raise ValueError(
                f"Proxy backend prefix {route.backend_prefix!r} is not represented in {MANIFEST_PATH}"
            )

    for path in module.EXPLICIT_FRONTEND_PATHS:
        if not isinstance(path, str) or not path.startswith("/api/"):
            raise ValueError(f"Explicit proxy exception path must be an API path: {path!r}")


def _render(module) -> str:
    lines = [
        "/**",
        " * Generated from packages/shared/src/api_proxy_routes.py and packages/sdk/openapi/routes.json.",
        " * Do not edit by hand.",
        " */",
        "",
        "export const API_PROXY_ROUTES = [",
    ]

    for route in module.PROXY_ROUTES:
        lines.append(
            "  { frontendPrefix: '%s', backendPrefix: '%s' },"
            % (route.frontend_prefix, route.backend_prefix)
        )

    lines.extend(
        [
            "] as const;",
            "",
            "export type ApiProxyRoute = (typeof API_PROXY_ROUTES)[number];",
            "",
            "export const API_PROXY_EXPLICIT_PATHS = [",
        ]
    )

    for path in module.EXPLICIT_FRONTEND_PATHS:
        lines.append(f"  '{path}',")

    lines.extend(
        [
            "] as const;",
            "",
            "export type ApiProxyExplicitPath = (typeof API_PROXY_EXPLICIT_PATHS)[number];",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    module = _load_contract()
    available_paths = _load_available_paths()
    if not available_paths:
        raise ValueError(
            f"No backend paths were loaded from {MANIFEST_PATH} or {OPENAPI_PATH}"
        )
    _validate_backend_targets(module, available_paths)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(_render(module), encoding="utf-8")
    print(f"Generated {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
