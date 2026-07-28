#!/usr/bin/env python3
"""Export a live FastAPI route manifest to packages/sdk/openapi/routes.json."""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from fastapi.routing import APIRoute

from tooling.generators.route_inventory_shared import (
    API_V1_PREFIX,
    METHOD_ORDER,
    method_sort_key,
    normalize_tags,
    normalize_text,
    strip_version_prefix,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
OUTPUT_PATH = REPO_ROOT / "packages" / "sdk" / "openapi" / "routes.json"

os.environ.setdefault("JWT_SECRET_KEY", "dev-route-manifest-export-secret")

_PATH_CONVERTER_RE = re.compile(r"{([^}:]+):[^}]+}")


@dataclass(frozen=True)
class RouteRecord:
    method: str
    path: str
    logical_path: str
    summary: str
    tags: tuple[str, ...]
    operation_id: str
    include_in_schema: bool
    compatibility_aliases: tuple[str, ...]
    canonical_path: str
    deprecated: bool
    replacement_path: str | None


def _build_operation_index(
    schema: dict[str, object],
) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    paths = schema.get("paths", {})
    if not isinstance(paths, dict):
        return index

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

            operation_record = {**operation, "x-goblin-openapi-path": path}
            index[(logical_path, upper_method)] = operation_record
            index[(path, upper_method)] = operation_record
            index[(_strip_path_converters(logical_path), upper_method)] = (
                operation_record
            )
            index[(_strip_path_converters(path), upper_method)] = operation_record

    return index


def _strip_path_converters(path: str) -> str:
    return _PATH_CONVERTER_RE.sub(r"{\1}", path)


def _route_key(method: str, path: str) -> tuple[str, str]:
    return (method, _strip_path_converters(path))


def _operation_records_from_schema(schema: dict[str, object]) -> list[RouteRecord]:
    records: list[RouteRecord] = []
    paths = schema.get("paths", {})
    if not isinstance(paths, dict):
        return records

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

            replacement_path = (
                normalize_text(
                    operation.get("x-goblin-replaced-by"),
                    fallback="",
                )
                or None
            )

            records.append(
                RouteRecord(
                    method=upper_method,
                    path=path,
                    logical_path=logical_path,
                    summary=normalize_text(
                        operation.get("summary") or operation.get("description"),
                        fallback="-",
                    ),
                    tags=normalize_tags(operation.get("tags")),
                    operation_id=normalize_text(
                        operation.get("operationId"),
                        fallback="-",
                    ),
                    include_in_schema=True,
                    compatibility_aliases=(),
                    canonical_path=path,
                    deprecated=bool(operation.get("deprecated", False)),
                    replacement_path=replacement_path,
                )
            )

    return records


def _route_records_from_app(
    api_app, schema: dict[str, object] | None = None
) -> list[RouteRecord]:
    operation_index = _build_operation_index(schema or {})
    records: list[RouteRecord] = []

    for route in api_app.routes:
        if not isinstance(route, APIRoute):
            continue

        path = getattr(route, "path", "")
        if not isinstance(path, str) or not path:
            continue

        raw_logical_path = strip_version_prefix(path)
        include_in_schema = bool(getattr(route, "include_in_schema", True))
        if not include_in_schema:
            continue

        methods = sorted(
            (
                method.upper()
                for method in getattr(route, "methods", set()) or set()
                if method.upper() not in {"HEAD", "OPTIONS"}
            ),
            key=method_sort_key,
        )

        for method in methods:
            operation = (
                operation_index.get((raw_logical_path, method))
                or operation_index.get((path, method))
                or operation_index.get(
                    (_strip_path_converters(raw_logical_path), method)
                )
                or operation_index.get((_strip_path_converters(path), method))
            )
            schema_path = (operation or {}).get("x-goblin-openapi-path")
            record_path = (
                schema_path
                if include_in_schema and isinstance(schema_path, str)
                else path
            )
            logical_path = strip_version_prefix(record_path)

            summary = normalize_text(
                (operation or {}).get("summary")
                or (operation or {}).get("description")
                or getattr(route, "summary", None)
                or getattr(route, "description", None)
                or getattr(route, "name", None),
                fallback="-",
            )
            tags = normalize_tags(
                (operation or {}).get("tags") or getattr(route, "tags", None)
            )
            operation_id = normalize_text(
                (operation or {}).get("operationId")
                or getattr(route, "operation_id", None)
                or getattr(route, "name", None),
                fallback="-",
            )
            openapi_extra = getattr(route, "openapi_extra", None)
            if not isinstance(openapi_extra, dict):
                openapi_extra = {}
            replacement_path = (
                normalize_text(
                    (operation or {}).get("x-goblin-replaced-by")
                    or openapi_extra.get("x-goblin-replaced-by"),
                    fallback="",
                )
                or None
            )

            records.append(
                RouteRecord(
                    method=method,
                    path=record_path,
                    logical_path=logical_path,
                    summary=summary,
                    tags=tags,
                    operation_id=operation_id,
                    include_in_schema=include_in_schema,
                    compatibility_aliases=(),
                    canonical_path=record_path,
                    deprecated=bool(
                        (operation or {}).get(
                            "deprecated", getattr(route, "deprecated", False)
                        )
                    ),
                    replacement_path=replacement_path,
                )
            )

    existing_operations = {(record.method, record.path) for record in records}
    equivalent_operations = {
        _route_key(record.method, record.path) for record in records
    }
    for schema_record in _operation_records_from_schema(schema or {}):
        schema_key = (schema_record.method, schema_record.path)
        equivalent_schema_key = _route_key(schema_record.method, schema_record.path)
        if (
            schema_key not in existing_operations
            and equivalent_schema_key not in equivalent_operations
        ):
            records.append(schema_record)
            existing_operations.add(schema_key)
            equivalent_operations.add(equivalent_schema_key)

    alias_map: dict[tuple[str, str], list[str]] = defaultdict(list)
    for record in records:
        alias_map[(record.method, record.logical_path)].append(record.path)

    canonical_map: dict[tuple[str, str], str] = {}
    for key, paths in alias_map.items():
        canonical_map[key] = sorted(
            set(paths),
            key=lambda candidate: (not candidate.startswith(API_V1_PREFIX), candidate),
        )[0]

    finalized: list[RouteRecord] = []
    for record in records:
        canonical_path = canonical_map[(record.method, record.logical_path)]
        aliases = tuple(
            alias
            for alias in sorted(set(alias_map[(record.method, record.logical_path)]))
            if alias != record.path
        )
        finalized.append(
            RouteRecord(
                method=record.method,
                path=record.path,
                logical_path=record.logical_path,
                summary=record.summary,
                tags=record.tags,
                operation_id=record.operation_id,
                include_in_schema=record.include_in_schema,
                compatibility_aliases=aliases,
                canonical_path=canonical_path,
                deprecated=record.deprecated or record.path != canonical_path,
                replacement_path=record.replacement_path
                or (canonical_path if canonical_path != record.path else None),
            )
        )

    finalized.sort(
        key=lambda record: (
            record.path,
            method_sort_key(record.method),
            record.logical_path,
            record.operation_id,
        )
    )
    return finalized


def build_manifest(
    api_app, schema: dict[str, object] | None = None
) -> dict[str, object]:
    schema = schema or api_app.openapi()
    routes = _route_records_from_app(api_app, schema)

    public_routes = [route for route in routes if route.include_in_schema]
    versioned_routes = [
        route for route in public_routes if route.path.startswith(API_V1_PREFIX)
    ]
    alias_routes = [route for route in public_routes if route.compatibility_aliases]

    return {
        "schema_version": 1,
        "api_v1_prefix": API_V1_PREFIX,
        "route_count": len(routes),
        "public_route_count": len(public_routes),
        "versioned_route_count": len(versioned_routes),
        "alias_route_count": len(alias_routes),
        "routes": [
            {
                **asdict(route),
                "tags": list(route.tags),
                "compatibility_aliases": list(route.compatibility_aliases),
            }
            for route in routes
        ],
    }


def export_manifest(output_path: Path = OUTPUT_PATH) -> dict[str, object]:
    if str(API_SRC) not in sys.path:
        sys.path.insert(0, str(API_SRC))

    from api.main import app  # noqa: E402

    schema = app.openapi()
    manifest = build_manifest(app, schema=schema)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Exported route manifest to {output_path}")
    return manifest


def main() -> int:
    export_manifest()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
