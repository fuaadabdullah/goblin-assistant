from __future__ import annotations

import json
from pathlib import Path

from tooling.quality.api_path_validation import validate_frontend_api_paths


def _write_manifest(path: Path, routes: list[str]) -> None:
    payload = {
        "routes": [
            {
                "path": route,
                "method": "GET",
                "logical_path": route,
                "summary": route,
                "tags": [],
                "operation_id": route.replace("/", "_"),
                "include_in_schema": True,
                "compatibility_aliases": [],
            }
            for route in routes
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_validate_frontend_api_paths_allows_manifest_and_proxy_routes(tmp_path: Path) -> None:
    frontend_app = tmp_path / "apps" / "web" / "app"
    frontend_src = tmp_path / "apps" / "web" / "src"
    frontend_api = frontend_app / "api"
    frontend_api.mkdir(parents=True)
    frontend_src.mkdir(parents=True)

    (frontend_app / "page.tsx").write_text(
        """
        const backend = '/api/v1/chat/conversations/conv-1';
        const proxy = '/api/generate';
        """,
        encoding="utf-8",
    )
    (frontend_src / "client.ts").write_text(
        """
        const absolute = 'http://localhost:8001/api/v1/settings/providers/openai';
        """,
        encoding="utf-8",
    )
    (frontend_api / "generate" / "route.ts").parent.mkdir(parents=True)
    (frontend_api / "generate" / "route.ts").write_text("export const runtime = 'nodejs';\n", encoding="utf-8")

    manifest_path = tmp_path / "routes.json"
    _write_manifest(
        manifest_path,
        [
            "/api/v1/chat/conversations/{conversation_id}",
            "/api/v1/settings/providers/{provider_name}",
        ],
    )

    violations = validate_frontend_api_paths(
        frontend_roots=(frontend_app, frontend_src),
        manifest_path=manifest_path,
        frontend_api_dir=frontend_api,
    )

    assert violations == []


def test_validate_frontend_api_paths_reports_unknown_paths(tmp_path: Path) -> None:
    frontend_app = tmp_path / "apps" / "web" / "app"
    frontend_src = tmp_path / "apps" / "web" / "src"
    frontend_api = frontend_app / "api"
    frontend_api.mkdir(parents=True)
    frontend_src.mkdir(parents=True)

    (frontend_app / "page.tsx").write_text(
        "const bad = '/api/v1/unknown/feature';\n",
        encoding="utf-8",
    )

    manifest_path = tmp_path / "routes.json"
    _write_manifest(manifest_path, ["/api/v1/chat/conversations/{conversation_id}"])

    violations = validate_frontend_api_paths(
        frontend_roots=(frontend_app, frontend_src),
        manifest_path=manifest_path,
        frontend_api_dir=frontend_api,
    )

    assert len(violations) == 1
    assert violations[0].normalized == "/api/v1/unknown/feature"
