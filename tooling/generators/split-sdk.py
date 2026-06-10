#!/usr/bin/env python3
"""
Post-generation splitter for the OpenAPI TypeScript SDK.

Reads the monolithic openapi.ts produced by openapi-typescript and splits it
into three domain-scoped modules so TypeScript can cache each independently:

  components.ts  — schema/model types (~1,400 lines, no imports)
  operations.ts  — per-endpoint request/response types (~7,000 lines)
  paths.ts       — route definitions + webhooks (~4,700 lines)

Usage (called automatically by generate-sdk-client.sh):
  python3 tooling/generators/split-sdk.py
"""

from __future__ import annotations

import re
from pathlib import Path

NOTICE = """\
/**
 * This file is generated. Do not edit directly.
 * Re-run: pnpm --filter @goblin/sdk generate
 */
"""

# Order must match the order they appear in openapi.ts
_SECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("paths", re.compile(r"^export interface paths \{")),
    ("webhooks", re.compile(r"^export type webhooks =")),
    ("components", re.compile(r"^export interface components \{")),
    ("defs", re.compile(r"^export type \$defs =")),
    ("operations", re.compile(r"^export interface operations \{")),
]


def _find_boundaries(lines: list[str]) -> dict[str, int]:
    found: dict[str, int] = {}
    remaining = dict(_SECTION_PATTERNS)
    for i, line in enumerate(lines):
        for name, pat in list(remaining.items()):
            if pat.match(line):
                found[name] = i
                del remaining[name]
        if not remaining:
            break
    return found


def _extract(lines: list[str], name: str, order: list[str], starts: dict[str, int]) -> str:
    start = starts[name]
    idx = order.index(name)
    end = starts[order[idx + 1]] if idx + 1 < len(order) else len(lines)
    return "\n".join(lines[start:end]).rstrip()


def split(src: Path, out_dir: Path) -> None:
    lines = src.read_text().splitlines()
    starts = _find_boundaries(lines)
    order = [name for name, _ in _SECTION_PATTERNS if name in starts]

    def get(name: str) -> str:
        return _extract(lines, name, order, starts)

    # components.ts — standalone (no cross-file imports needed)
    (out_dir / "components.ts").write_text(
        NOTICE
        + "\n"
        + get("components")
        + "\n"
        + get("defs")
        + "\n"
    )

    # operations.ts — request/response types that reference component schemas
    (out_dir / "operations.ts").write_text(
        NOTICE
        + 'import type { components } from "./components";\n'
        + "\n"
        + get("operations")
        + "\n"
    )

    # paths.ts — route map referencing operations; also carries the trivial webhooks type
    (out_dir / "paths.ts").write_text(
        NOTICE
        + 'import type { operations } from "./operations";\n'
        + "\n"
        + get("paths")
        + "\n"
        + get("webhooks")
        + "\n"
    )

    sizes = {
        "components": len(get("components").splitlines()),
        "operations": len(get("operations").splitlines()),
        "paths": len(get("paths").splitlines()),
    }
    print(
        f"Split openapi.ts ({len(lines)} lines) → "
        + ", ".join(f"{k}.ts ({v} lines)" for k, v in sizes.items())
    )


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[2]
    src = repo_root / "packages/sdk/src/generated/openapi.ts"
    out = repo_root / "packages/sdk/src/generated"
    split(src, out)
