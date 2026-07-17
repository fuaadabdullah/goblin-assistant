#!/usr/bin/env python3
"""Generate TypeScript route-prefix constants from the shared Python contract."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "packages" / "shared" / "src" / "api_routes.py"
OUTPUT_PATH = REPO_ROOT / "packages" / "shared" / "src" / "constants" / "routes.ts"


def _load_contract():
    spec = importlib.util.spec_from_file_location("api_routes_contract", CONTRACT_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load API route contract: {CONTRACT_PATH}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _render(module) -> str:
    lines = [
        "/**",
        " * Generated from packages/shared/src/api_routes.py.",
        " * Do not edit by hand.",
        " */",
        "",
        f"export const API_PREFIX = '{module.API_PREFIX}' as const;",
        f"export const API_VERSION = '{module.API_VERSION}' as const;",
        f"export const V1_API_PREFIX = '{module.API_V1_PREFIX}' as const;",
    ]

    for name in (
        "V1_CHAT_PREFIX",
        "V1_AUTH_PREFIX",
        "V1_PROVIDERS_PREFIX",
        "V1_HEALTH_PREFIX",
        "V1_SETTINGS_PREFIX",
    ):
        lines.append(f"export const {name} = '{getattr(module, name)}' as const;")

    lines.extend(
        [
            "",
            "export const ROUTE_PREFIXES = {",
        ]
    )

    for key, value in sorted(module.ROUTE_PREFIXES.items()):
        lines.append(f"  {key}: '{value}',")

    lines.extend(
        [
            "} as const;",
            "",
            "export type SharedRoutePrefix =",
        ]
    )

    prefix_values = [module.API_V1_PREFIX, *module.ROUTE_PREFIXES.values()]
    for index, value in enumerate(dict.fromkeys(prefix_values)):
        suffix = ";" if index == len(dict.fromkeys(prefix_values)) - 1 else ""
        lines.append(f"  | '{value}'{suffix}")

    lines.extend(
        [
            "",
            "export const buildVersionedPath = (...segments: string[]): string => {",
            "  const cleaned = segments.map((segment) => segment.trim().replace(/^\\/|\\/$/g, '')).filter(Boolean);",
            "  return cleaned.length === 0 ? V1_API_PREFIX : `${V1_API_PREFIX}/${cleaned.join('/')}`;",
            "};",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    module = _load_contract()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(_render(module), encoding="utf-8")
    print(f"Generated {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
