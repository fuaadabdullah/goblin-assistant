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
OUTPUT_PATH = REPO_ROOT / "packages" / "shared" / "src" / "generated" / "api-proxy-routes.ts"


def _load_contract():
    spec = importlib.util.spec_from_file_location("api_proxy_routes_contract", CONTRACT_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load API proxy route contract: {CONTRACT_PATH}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_manifest_paths() -> list[str]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    routes = manifest.get("routes", [])
    if not isinstance(routes, list):
        return []

    paths: list[str] = []
    for route in routes:
        if not isinstance(route, dict):
            continue
        path = route.get("path")
        if isinstance(path, str) and path:
            paths.append(path.rstrip("/") if path != "/" else "/")
    return paths


def _matches_prefix(path: str, prefix: str) -> bool:
    normalized_path = path.rstrip("/") if path != "/" else "/"
    normalized_prefix = prefix.rstrip("/") if prefix != "/" else "/"
    return normalized_path == normalized_prefix or normalized_path.startswith(f"{normalized_prefix}/")


def _validate_proxy_prefix_routes(module, manifest_paths: list[str]) -> None:
    """ProxyPrefixSpec: at least one manifest route must start with backend_prefix."""
    for route in getattr(module, "PROXY_PREFIX_ROUTES", module.PROXY_ROUTES):
        backend_prefix = route.backend_prefix.rstrip("/") if route.backend_prefix != "/" else "/"
        if not any(_matches_prefix(path, backend_prefix) for path in manifest_paths):
            raise ValueError(
                f"ProxyPrefixSpec backend prefix {route.backend_prefix!r} has no matching routes "
                f"in {MANIFEST_PATH}. If only a single endpoint exists, use ProxyEndpointSpec "
                f"instead — it enforces an exact match and prevents false positives."
            )


def _validate_proxy_endpoint_routes(module, manifest_paths: list[str]) -> None:
    """ProxyEndpointSpec: backend_path must exist exactly in the manifest."""
    for route in getattr(module, "PROXY_ENDPOINT_ROUTES", ()):
        backend_path = route.backend_path.rstrip("/") if route.backend_path != "/" else "/"
        if not any(p == backend_path for p in manifest_paths):
            raise ValueError(
                f"ProxyEndpointSpec backend path {route.backend_path!r} does not exist in "
                f"{MANIFEST_PATH}. ProxyEndpointSpec requires an exact manifest match — "
                f"no prefix or startswith logic is applied."
            )


def _validate_backend_targets(module, manifest_paths: list[str]) -> None:
    _validate_proxy_prefix_routes(module, manifest_paths)
    _validate_proxy_endpoint_routes(module, manifest_paths)

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
        "export const API_PROXY_PREFIX_ROUTES = [",
    ]

    for route in getattr(module, "PROXY_PREFIX_ROUTES", module.PROXY_ROUTES):
        lines.append(
            "  { frontendPrefix: '%s', backendPrefix: '%s' },"
            % (route.frontend_prefix, route.backend_prefix)
        )

    lines.extend(
        [
            "] as const;",
            "",
            "export type ApiProxyPrefixRoute = (typeof API_PROXY_PREFIX_ROUTES)[number];",
            "",
            "export const API_PROXY_ENDPOINT_ROUTES = [",
        ]
    )

    for route in getattr(module, "PROXY_ENDPOINT_ROUTES", ()):
        lines.append(
            "  { frontendPath: '%s', backendPath: '%s' },"
            % (route.frontend_path, route.backend_path)
        )

    lines.extend(
        [
            "] as const;",
            "",
            "export type ApiProxyEndpointRoute = (typeof API_PROXY_ENDPOINT_ROUTES)[number];",
            "",
            "export type ApiProxyRoute =",
            "  | ({ kind: 'prefix' } & ApiProxyPrefixRoute)",
            "  | ({ kind: 'endpoint' } & ApiProxyEndpointRoute);",
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
    manifest_paths = _load_manifest_paths()
    _validate_backend_targets(module, manifest_paths)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(_render(module), encoding="utf-8")
    print(f"Generated {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
