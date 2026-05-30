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
    schema = {
        "paths": {
            "/auth/login": {
                "post": {
                    "summary": "Start a session",
                    "tags": ["auth"],
                    "operationId": "auth_login",
                }
            },
            "/api/chat": {
                "post": {
                    "description": "Send a prompt to chat.",
                    "tags": ["chat"],
                    "operationId": "chat_create",
                }
            },
            "/api/v1/api/chat": {
                "post": {
                    "summary": "Compatibility chat entrypoint",
                    "tags": ["api"],
                    "operationId": "chat_create_v1",
                }
            },
        }
    }

    markdown = build_markdown(schema)

    assert "# API Route Inventory" in markdown
    assert "- **Paths**: 3" in markdown
    assert "- **Operations**: 3" in markdown
    assert "- **Compatibility alias operations (`/api/v1`)**: 1" in markdown
    assert "| `/auth` | 1 |" in markdown
    assert "| `/api/chat` | 1 |" in markdown
    assert "## Compatibility aliases" in markdown
    assert (
        "| POST | /api/v1/api/chat | Compatibility chat entrypoint | api | "
        "chat_create_v1 |"
    ) in markdown


def test_collect_operations_extracts_operation_metadata():
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

    operations = collect_operations(schema)

    assert len(operations) == 1
    operation = operations[0]
    assert operation.group == "/api/privacy"
    assert operation.method == "POST"
    assert operation.summary == "Export user data"
    assert operation.tags == ("privacy", "gdpr")
    assert operation.operation_id == "export_privacy_data"
