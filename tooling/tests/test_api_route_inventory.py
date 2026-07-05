from __future__ import annotations

from tooling.generators.api_route_inventory import (
    build_markdown,
    collect_operations,
    group_for_path,
)


def test_group_for_path_collapses_alias_and_top_level_routes():
    assert group_for_path("/") == "/"
    assert group_for_path("/auth/login") == "/auth"
    assert group_for_path("/api/chat") == "/api/chat"
    assert group_for_path("/api/v1/api/chat") == "/api/v1"


def test_build_markdown_summarizes_groups_and_aliases():
    routes_manifest = {
        "route_count": 4,
        "public_route_count": 4,
        "routes": [
            {
                "method": "POST",
                "path": "/auth/login",
                "logical_path": "/auth/login",
                "summary": "Start a session",
                "tags": ["auth"],
                "operation_id": "auth_login",
                "include_in_schema": True,
                "compatibility_aliases": [],
            },
            {
                "method": "GET",
                "path": "/settings",
                "logical_path": "/settings",
                "summary": "Read settings",
                "tags": ["settings"],
                "operation_id": "read_settings",
                "include_in_schema": True,
                "compatibility_aliases": ["/api/v1/settings"],
            },
            {
                "method": "GET",
                "path": "/api/v1/settings",
                "logical_path": "/settings",
                "summary": "Read settings",
                "tags": ["settings"],
                "operation_id": "read_settings_v1",
                "include_in_schema": True,
                "compatibility_aliases": ["/settings"],
            },
            {
                "method": "POST",
                "path": "/api/v1/api/chat",
                "logical_path": "/api/chat",
                "summary": "Compatibility chat entrypoint",
                "tags": ["api"],
                "operation_id": "chat_create_v1",
                "include_in_schema": True,
                "compatibility_aliases": [],
            },
        ],
    }

    schema = {
        "paths": {
            "/auth/login": {
                "post": {
                    "summary": "Start a session",
                    "tags": ["auth"],
                    "operationId": "auth_login",
                }
            },
            "/settings": {
                "get": {
                    "summary": "Read settings",
                    "tags": ["settings"],
                    "operationId": "read_settings",
                }
            },
            "/api/chat": {
                "post": {
                    "description": "Send a prompt to chat.",
                    "tags": ["chat"],
                    "operationId": "chat_create",
                }
            },
        }
    }

    markdown = build_markdown(routes_manifest, schema)

    assert "# API Route Inventory" in markdown
    assert "- **Mounted paths**: 4" in markdown
    assert "- **Operations**: 4" in markdown
    assert "- **OpenAPI paths**: 3" in markdown
    assert "- **Versioned compatibility alias operations (`/api/v1`)**: 2" in markdown
    assert "- **Legacy dual-mount operations**: 1" in markdown
    assert "| `/auth` | 1 |" in markdown
    assert "| `/settings` | 1 |" in markdown
    assert "| `/api/v1` | 2 |" in markdown
    assert "## Versioned compatibility aliases" in markdown
    assert "## Legacy dual mounts" in markdown
    assert (
        "| POST | /api/v1/api/chat | /api/chat | Send a prompt to chat. | api | "
        "chat_create_v1 |"
    ) in markdown


def test_collect_operations_extracts_operation_metadata():
    routes_manifest = {
        "routes": [
            {
                "method": "POST",
                "path": "/api/privacy/export",
                "logical_path": "/api/privacy/export",
                "summary": "Export user data",
                "tags": ["privacy", "gdpr"],
                "operation_id": "export_privacy_data",
                "include_in_schema": True,
                "compatibility_aliases": [],
            }
        ]
    }
    schema = {
        "paths": {
            "/api/privacy/export": {
                "post": {
                    "summary": "Export user data",
                    "tags": ["privacy", "gdpr"],
                    "operationId": "export_privacy_data",
                }
            }
        }
    }

    operations = collect_operations(routes_manifest, schema)

    assert len(operations) == 1
    operation = operations[0]
    assert operation.group == "/api/privacy"
    assert operation.method == "POST"
    assert operation.summary == "Export user data"
    assert operation.tags == ("privacy", "gdpr")
    assert operation.operation_id == "export_privacy_data"
    assert operation.logical_path == "/api/privacy/export"
    assert operation.compatibility_aliases == ()
