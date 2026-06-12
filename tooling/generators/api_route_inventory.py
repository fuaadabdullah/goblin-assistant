#!/usr/bin/env python3
"""Generate a markdown inventory of backend API routes from OpenAPI.

The repo already checks in `packages/sdk/openapi/openapi.json`.
This module turns that schema into a human-readable route inventory grouped
by the path prefixes that the current FastAPI app exposes.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_PATH = (
    REPO_ROOT / "packages" / "sdk" / "openapi" / "openapi.json"
)
GENERATED_OUTPUT_PATH = (
    REPO_ROOT / "docs" / "backend" / "API_ROUTE_INVENTORY.generated.md"
)

METHOD_ORDER = {
    "DELETE": 0,
    "GET": 1,
    "HEAD": 2,
    "OPTIONS": 3,
    "PATCH": 4,
    "POST": 5,
    "PUT": 6,
}


@dataclass(frozen=True)
class RouteOperation:
    path: str
    method: str
    summary: str
    tags: tuple[str, ...]
    operation_id: str
    group: str


def _normalize_summary(operation: dict[str, object]) -> str:
    for key in ("summary", "description", "operationId"):
        value = operation.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())
    return "—"


def _normalize_tags(operation: dict[str, object]) -> tuple[str, ...]:
    tags = operation.get("tags")
    if not isinstance(tags, list):
        return ()
    return tuple(str(tag) for tag in tags if str(tag).strip())


def group_for_path(path: str) -> str:
    parts = [segment for segment in path.split("/") if segment]
    if not parts:
        return "/"
    if parts[0] == "api" and len(parts) > 1:
        if parts[1] == "v1":
            return "/api/v1"
        return f"/api/{parts[1]}"
    return f"/{parts[0]}"


def collect_operations(schema: dict[str, object]) -> list[RouteOperation]:
    paths = schema.get("paths", {})
    if not isinstance(paths, dict):
        return []

    operations: list[RouteOperation] = []
    for path, methods in paths.items():
        if not isinstance(path, str) or not isinstance(methods, dict):
            continue

        for method, operation in methods.items():
            if not isinstance(method, str) or not isinstance(operation, dict):
                continue
            upper_method = method.upper()
            if upper_method not in METHOD_ORDER:
                continue

            operations.append(
                RouteOperation(
                    path=path,
                    method=upper_method,
                    summary=_normalize_summary(operation),
                    tags=_normalize_tags(operation),
                    operation_id=str(operation.get("operationId") or ""),
                    group=group_for_path(path),
                )
            )

    operations.sort(
        key=lambda op: (
            op.group,
            op.path,
            METHOD_ORDER[op.method],
            op.operation_id,
        )
    )
    return operations


def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _format_tags(tags: Iterable[str]) -> str:
    rendered = ", ".join(tag for tag in tags if tag)
    return rendered or "—"


def build_markdown(schema: dict[str, object]) -> str:
    operations = collect_operations(schema)
    path_groups: dict[str, list[RouteOperation]] = defaultdict(list)
    for operation in operations:
        path_groups[operation.group].append(operation)

    alias_operations = [op for op in operations if op.group == "/api/v1"]
    path_count = len({op.path for op in operations})
    group_counts = Counter(op.group for op in operations)

    lines: list[str] = [
        "---",
        'title: "API Route Inventory"',
        (
            'description: "Generated backend route inventory from the '
            'checked-in OpenAPI schema"'
        ),
        "---",
        "",
        "# API Route Inventory",
        "",
        "Generated from `packages/sdk/openapi/openapi.json`.",
        "",
        "## Snapshot",
        "",
        f"- **Paths**: {path_count}",
        f"- **Operations**: {len(operations)}",
        (
            "- **Compatibility alias operations (`/api/v1`)**: "
            f"{len(alias_operations)}"
        ),
        "",
        "## Route groups",
        "",
        "| Group | Operations |",
        "| --- | ---: |",
    ]

    for group in sorted(
        group_counts,
        key=lambda key: (-group_counts[key], key),
    ):
        lines.append(f"| `{_escape_cell(group)}` | {group_counts[group]} |")

    if alias_operations:
        lines.extend(
            [
                "",
                "## Compatibility aliases",
                "",
                (
                    "The `/api/v1` routes are the current compatibility layer "
                    "for frontend and proxy consumers that still expect "
                    "versioned paths."
                ),
                "",
                "| Method | Path | Summary | Tags | Operation ID |",
                "| --- | --- | --- | --- | --- |",
            ]
        )

        for operation in alias_operations:
            lines.append(
                "| "
                f"{_escape_cell(operation.method)} | "
                f"{_escape_cell(operation.path)} | "
                f"{_escape_cell(operation.summary)} | "
                f"{_escape_cell(_format_tags(operation.tags))} | "
                f"{_escape_cell(operation.operation_id or '—')} |"
            )

    for group in sorted(path_groups):
        lines.extend(
            [
                "",
                f"## {group}",
                "",
                "| Method | Path | Summary | Tags | Operation ID |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for operation in path_groups[group]:
            lines.append(
                "| "
                f"{_escape_cell(operation.method)} | "
                f"{_escape_cell(operation.path)} | "
                f"{_escape_cell(operation.summary)} | "
                f"{_escape_cell(_format_tags(operation.tags))} | "
                f"{_escape_cell(operation.operation_id or '—')} |"
            )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            (
                "- Regenerate this file after changing FastAPI routes or the "
                "OpenAPI export."
            ),
            (
                "- The route inventory is intentionally grouped by path "
                "prefix so frontend contract work can spot mismatches "
                "quickly."
            ),
            (
                "- Route summaries come from FastAPI OpenAPI metadata, so "
                "improving endpoint annotations will improve this inventory "
                "automatically."
            ),
        ]
    )

    return "\n".join(lines) + "\n"


def load_schema(schema_path: Path) -> dict[str, object]:
    return json.loads(schema_path.read_text(encoding="utf-8"))


def generate_inventory(schema_path: Path, output_path: Path) -> str:
    schema = load_schema(schema_path)
    markdown = build_markdown(schema)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return markdown


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a backend API route inventory from OpenAPI."
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
    output_path = Path(args.output_path)
    generated = build_markdown(load_schema(schema_path))

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
