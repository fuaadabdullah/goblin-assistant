#!/usr/bin/env python3
"""Generate a markdown inventory of backend API routes from OpenAPI + manifest."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from tooling.generators.route_inventory_shared import (
    API_V1_PREFIX,
    METHOD_ORDER,
    group_for_path,
    method_sort_key,
    normalize_tags,
    normalize_text,
    strip_version_prefix,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_PATH = REPO_ROOT / "packages" / "sdk" / "openapi" / "openapi.json"
DEFAULT_ROUTES_PATH = REPO_ROOT / "packages" / "sdk" / "openapi" / "routes.json"
GENERATED_OUTPUT_PATH = REPO_ROOT / "docs" / "backend" / "API_ROUTE_INVENTORY.generated.md"


@dataclass(frozen=True)
class RouteOperation:
    path: str
    logical_path: str
    method: str
    summary: str
    tags: tuple[str, ...]
    operation_id: str
    group: str
    compatibility_aliases: tuple[str, ...]
    canonical_path: str
    deprecated: bool
    replacement_path: str | None


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_summary(operation: dict[str, object] | None) -> str:
    if not operation:
        return "-"
    return normalize_text(
        operation.get("summary") or operation.get("description") or operation.get("operationId"),
        fallback="-",
    )


def _schema_operation_index(schema: dict[str, object]) -> dict[tuple[str, str], dict[str, object]]:
    paths = schema.get("paths", {})
    if not isinstance(paths, dict):
        return {}

    index: dict[tuple[str, str], dict[str, object]] = {}
    for path, methods in paths.items():
        if not isinstance(path, str) or not isinstance(methods, dict):
            continue
        logical_path = strip_version_prefix(path)
        for method, operation in methods.items():
            if not isinstance(method, str) or not isinstance(operation, dict):
                continue
            upper_method = method.upper()
            if upper_method not in METHOD_ORDER:
                continue
            index[(logical_path, upper_method)] = operation
            index[(path, upper_method)] = operation
    return index


def _normalise_route_manifest(routes_manifest: dict[str, object]) -> list[dict[str, object]]:
    routes = routes_manifest.get("routes", [])
    if not isinstance(routes, list):
        return []

    normalised: list[dict[str, object]] = []
    for route in routes:
        if not isinstance(route, dict):
            continue
        path = route.get("path")
        method = route.get("method")
        if not isinstance(path, str) or not isinstance(method, str):
            continue
        normalised.append(route)
    return normalised


def collect_operations(
    routes_manifest: dict[str, object],
    schema: dict[str, object],
) -> list[RouteOperation]:
    schema_index = _schema_operation_index(schema)
    operations: list[RouteOperation] = []

    for route in _normalise_route_manifest(routes_manifest):
        if not bool(route.get("include_in_schema", True)):
            continue

        path = str(route["path"])
        method = str(route["method"]).upper()
        logical_path = str(route.get("logical_path") or strip_version_prefix(path))
        schema_operation = schema_index.get((logical_path, method)) or schema_index.get(
            (path, method)
        )

        summary = _normalize_summary(
            schema_operation
            or {
                "summary": route.get("summary"),
                "description": route.get("summary"),
                "operationId": route.get("operation_id"),
            }
        )
        tags = tuple(route.get("tags") or ())
        if not tags and schema_operation:
            tags = normalize_tags(schema_operation.get("tags"))

        operation_id = normalize_text(
            route.get("operation_id")
            or (schema_operation or {}).get("operationId")
            or route.get("path"),
            fallback="-",
        )
        compatibility_aliases = tuple(
            str(alias)
            for alias in route.get("compatibility_aliases", [])
            if isinstance(alias, str) and alias.strip()
        )
        canonical_path = str(route.get("canonical_path") or path)
        replacement_path_raw = route.get("replacement_path")
        replacement_path = (
            str(replacement_path_raw).strip()
            if isinstance(replacement_path_raw, str) and str(replacement_path_raw).strip()
            else None
        )

        operations.append(
            RouteOperation(
                path=path,
                logical_path=logical_path,
                method=method,
                summary=summary,
                tags=tags,
                operation_id=operation_id,
                group=group_for_path(path),
                compatibility_aliases=compatibility_aliases,
                canonical_path=canonical_path,
                deprecated=bool(route.get("deprecated", False)),
                replacement_path=replacement_path,
            )
        )

    operations.sort(
        key=lambda op: (
            op.group,
            op.path,
            method_sort_key(op.method),
            op.logical_path,
            op.operation_id,
        )
    )
    return operations


def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _format_tags(tags: Iterable[str]) -> str:
    rendered = ", ".join(tag for tag in tags if tag)
    return rendered or "-"


def build_markdown(routes_manifest: dict[str, object], schema: dict[str, object]) -> str:
    operations = collect_operations(routes_manifest, schema)
    path_groups: dict[str, list[RouteOperation]] = defaultdict(list)
    for operation in operations:
        path_groups[operation.group].append(operation)

    versioned_operations = [op for op in operations if op.path.startswith(API_V1_PREFIX)]
    legacy_alias_operations = [
        op
        for op in operations
        if op.compatibility_aliases and not op.path.startswith(API_V1_PREFIX)
    ]
    deprecated_operations = [op for op in operations if op.deprecated]
    hidden_route_count = int(routes_manifest.get("route_count", len(routes_manifest.get("routes", [])))) - int(
        routes_manifest.get("public_route_count", len(operations))
    )
    schema_paths = schema.get("paths", {})
    schema_path_count = len(schema_paths) if isinstance(schema_paths, dict) else 0

    lines: list[str] = [
        "---",
        'title: "API Route Inventory"',
        (
            'description: "Generated backend route inventory from the '
            'checked-in route manifest and OpenAPI schema"'
        ),
        "---",
        "",
        "# API Route Inventory",
        "",
        "Generated from `packages/sdk/openapi/routes.json` and `packages/sdk/openapi/openapi.json`.",
        "",
        "## Snapshot",
        "",
        f"- **Mounted paths**: {len({op.path for op in operations})}",
        f"- **Operations**: {len(operations)}",
        f"- **OpenAPI paths**: {schema_path_count}",
        f"- **Versioned operations (`/api/v1`)**: {len(versioned_operations)}",
        f"- **Legacy dual-mount operations**: {len(legacy_alias_operations)}",
        f"- **Deprecated operations**: {len(deprecated_operations)}",
        f"- **Hidden manifest operations**: {max(hidden_route_count, 0)}",
        "",
        "## Route groups",
        "",
        "| Group | Operations |",
        "| --- | ---: |",
    ]

    group_counts = Counter(op.group for op in operations)
    for group in sorted(group_counts, key=lambda key: (-group_counts[key], key)):
        lines.append(f"| `{_escape_cell(group)}` | {group_counts[group]} |")

    if versioned_operations:
        lines.extend(
            [
                "",
                "## Versioned public routes",
                "",
                "The `/api/v1` routes are the canonical public API surface.",
                "",
                "| Method | Path | Logical Path | Status | Replaced By | Summary | Tags | Operation ID |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for operation in versioned_operations:
            lines.append(
                "| "
                f"{_escape_cell(operation.method)} | "
                f"{_escape_cell(operation.path)} | "
                f"{_escape_cell(operation.logical_path)} | "
                f"{_escape_cell('deprecated' if operation.deprecated else 'stable')} | "
                f"{_escape_cell(operation.replacement_path or '-')} | "
                f"{_escape_cell(operation.summary)} | "
                f"{_escape_cell(_format_tags(operation.tags))} | "
                f"{_escape_cell(operation.operation_id or '-')} |"
            )

    if legacy_alias_operations:
        lines.extend(
            [
                "",
                "## Legacy dual mounts",
                "",
                (
                    "These routes are mounted both at their canonical path and "
                    "at one or more compatibility aliases."
                ),
                "",
                "| Method | Path | Logical Path | Aliases | Status | Replaced By | Summary | Tags | Operation ID |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for operation in legacy_alias_operations:
            aliases = ", ".join(operation.compatibility_aliases) or "-"
            lines.append(
                "| "
                f"{_escape_cell(operation.method)} | "
                f"{_escape_cell(operation.path)} | "
                f"{_escape_cell(operation.logical_path)} | "
                f"{_escape_cell(aliases)} | "
                f"{_escape_cell('deprecated' if operation.deprecated else 'stable')} | "
                f"{_escape_cell(operation.replacement_path or '-')} | "
                f"{_escape_cell(operation.summary)} | "
                f"{_escape_cell(_format_tags(operation.tags))} | "
                f"{_escape_cell(operation.operation_id or '-')} |"
            )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            (
                "- Regenerate this file after changing FastAPI routes, the route "
                "manifest, or the OpenAPI export."
            ),
            (
                "- The route inventory is intentionally grouped by mounted path "
                "prefix so frontend contract work can spot mismatches quickly."
            ),
            (
                "- Route summaries come from the OpenAPI schema when available, "
                "with manifest values used as a fallback."
            ),
        ]
    )

    return "\n".join(lines) + "\n"


def load_schema(schema_path: Path) -> dict[str, object]:
    return _load_json(schema_path)


def load_routes_manifest(routes_path: Path) -> dict[str, object]:
    return _load_json(routes_path)


def generate_inventory(
    schema_path: Path,
    routes_path: Path,
    output_path: Path,
) -> str:
    schema = load_schema(schema_path)
    routes_manifest = load_routes_manifest(routes_path)
    markdown = build_markdown(routes_manifest, schema)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return markdown


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a backend API route inventory from OpenAPI + manifest."
    )
    parser.add_argument(
        "--schema-path",
        default=str(DEFAULT_SCHEMA_PATH),
        help=(
            "Path to the OpenAPI JSON schema (default: "
            "packages/sdk/openapi/openapi.json)"
        ),
    )
    parser.add_argument(
        "--routes-path",
        default=str(DEFAULT_ROUTES_PATH),
        help=(
            "Path to the checked-in route manifest (default: "
            "packages/sdk/openapi/routes.json)"
        ),
    )
    parser.add_argument(
        "--output-path",
        default=str(GENERATED_OUTPUT_PATH),
        help=(
            "Path to the markdown inventory output (default: "
            "docs/backend/API_ROUTE_INVENTORY.generated.md)"
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Exit 1 if the generated markdown does not match the "
            "checked-in output"
        ),
    )
    args = parser.parse_args()

    schema_path = Path(args.schema_path)
    routes_path = Path(args.routes_path)
    output_path = Path(args.output_path)
    generated = build_markdown(load_routes_manifest(routes_path), load_schema(schema_path))

    if args.check:
        if not output_path.exists():
            print(
                f"ERROR: {output_path} does not exist. "
                "Run without --check to generate it."
            )
            return 1
        existing = output_path.read_text(encoding="utf-8")
        if existing != generated:
            print(
                f"ERROR: {output_path} is stale. Regenerate it with "
                "generate-api-route-inventory.py"
            )
            return 1
        print(f"OK: {output_path} is up-to-date")
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_path.write_text(generated, encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: Unable to write {output_path}: {exc}")
        return 1
    print(f"Generated {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
