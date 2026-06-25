"""
Project tools for Goblin Assistant.

Provides project scaffold and inspection tools backed by an explicit marker
file (.goblin-project.json) inside the existing goblin workspace sandbox.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..registry import ToolDefinition, ToolParameter, register_tool

PROJECT_MARKER = ".goblin-project.json"
PROJECT_SCHEMA_VERSION = "1.0"
REQUIRED_MARKER_FIELDS = {"name", "created_at", "version"}


def _get_base_dir() -> Path:
    raw = os.environ.get("GOBLIN_FILE_WORKSPACE", "~/goblin-workspace")
    return Path(raw).expanduser().resolve()


def _resolve_path(user_path: str) -> Path:
    base = _get_base_dir()
    candidate = (base / user_path).resolve()
    if base not in candidate.parents and candidate != base:
        raise ValueError(
            f"Path '{user_path}' resolves outside the workspace. "
            "All project operations must stay within the goblin workspace."
        )
    return candidate


def _load_marker(marker_path: Path) -> Dict[str, Any]:
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid {PROJECT_MARKER}: JSON parse error ({exc})") from exc
    if not isinstance(marker, dict):
        raise ValueError(f"Invalid {PROJECT_MARKER}: expected an object")

    missing = REQUIRED_MARKER_FIELDS - set(marker.keys())
    if missing:
        raise ValueError(f"Invalid {PROJECT_MARKER}: missing required fields {sorted(missing)}")

    if not isinstance(marker.get("name"), str) or not marker["name"].strip():
        raise ValueError(f"Invalid {PROJECT_MARKER}: 'name' must be a non-empty string")
    if not isinstance(marker.get("created_at"), str) or not marker["created_at"].strip():
        raise ValueError(f"Invalid {PROJECT_MARKER}: 'created_at' must be a non-empty string")
    if not isinstance(marker.get("version"), str) or not marker["version"].strip():
        raise ValueError(f"Invalid {PROJECT_MARKER}: 'version' must be a non-empty string")

    tags = marker.get("tags")
    if tags is not None and (
        not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags)
    ):
        raise ValueError(f"Invalid {PROJECT_MARKER}: 'tags' must be an array of strings")

    return marker


def _project_stats(project_dir: Path) -> Dict[str, Any]:
    file_count = 0
    directory_count = 0
    total_size_bytes = 0

    for entry in project_dir.rglob("*"):
        if entry.is_dir():
            directory_count += 1
            continue
        if entry.is_file():
            file_count += 1
            try:
                total_size_bytes += entry.stat().st_size
            except OSError:
                pass

    return {
        "file_count": file_count,
        "directory_count": directory_count,
        "total_size_bytes": total_size_bytes,
    }


async def _handle_create_project(
    name: str,
    path: str,
    confirm: bool,
    template: Optional[str] = None,
) -> Dict[str, Any]:
    def _create() -> Dict[str, Any]:
        if not confirm:
            return {
                "error": "create_project requires confirm=true for mutating operations",
            }

        try:
            project_dir = _resolve_path(path)
        except ValueError as exc:
            return {"error": str(exc)}

        marker_path = project_dir / PROJECT_MARKER
        if marker_path.exists():
            return {"error": f"Project marker already exists at: {path}/{PROJECT_MARKER}"}

        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "docs").mkdir(exist_ok=True)
        (project_dir / "src").mkdir(exist_ok=True)
        (project_dir / "data").mkdir(exist_ok=True)

        marker: Dict[str, Any] = {
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "version": PROJECT_SCHEMA_VERSION,
        }
        if template:
            marker["template"] = template

        marker_path.write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")
        return {
            "created": True,
            "project_path": str(project_dir),
            "marker_path": str(marker_path),
            "marker": marker,
        }

    return await asyncio.to_thread(_create)


async def _handle_list_projects(
    directory: str = ".",
    max_depth: int = 4,
) -> Dict[str, Any]:
    def _list() -> Dict[str, Any]:
        try:
            root = _resolve_path(directory)
        except ValueError as exc:
            return {"error": str(exc)}

        if not root.exists():
            return {"error": f"Directory not found: {directory}"}
        if not root.is_dir():
            return {"error": f"Path is not a directory: {directory}"}
        if max_depth < 0:
            return {"error": "max_depth must be >= 0"}

        base = _get_base_dir()
        projects: List[Dict[str, Any]] = []
        root_depth = len(root.parts)

        for marker_path in root.rglob(PROJECT_MARKER):
            project_dir = marker_path.parent
            depth = len(project_dir.parts) - root_depth
            if depth > max_depth:
                continue

            rel_path = str(project_dir.relative_to(base))
            try:
                marker = _load_marker(marker_path)
                projects.append(
                    {
                        "path": rel_path,
                        "name": marker["name"],
                        "version": marker["version"],
                        "created_at": marker["created_at"],
                        "template": marker.get("template"),
                        "tags": marker.get("tags", []),
                    }
                )
            except ValueError as exc:
                projects.append(
                    {
                        "path": rel_path,
                        "error": str(exc),
                    }
                )

        projects.sort(key=lambda item: item["path"])
        return {
            "projects": projects,
            "count": len(projects),
            "searched_directory": str(root),
        }

    return await asyncio.to_thread(_list)


async def _handle_get_project_info(path: str) -> Dict[str, Any]:
    def _info() -> Dict[str, Any]:
        try:
            project_dir = _resolve_path(path)
        except ValueError as exc:
            return {"error": str(exc)}

        if not project_dir.exists():
            return {"error": f"Path not found: {path}"}
        if not project_dir.is_dir():
            return {"error": f"Path is not a directory: {path}"}

        marker_path = project_dir / PROJECT_MARKER
        if not marker_path.exists():
            return {"error": f"Project marker not found: {path}/{PROJECT_MARKER}"}

        try:
            marker = _load_marker(marker_path)
        except ValueError as exc:
            return {"error": str(exc)}

        stats = _project_stats(project_dir)
        return {
            "path": str(project_dir),
            "marker_path": str(marker_path),
            "marker": marker,
            "stats": stats,
        }

    return await asyncio.to_thread(_info)


register_tool(
    ToolDefinition(
        name="create_project",
        description=(
            "Use when the user wants to scaffold a new project in the workspace. "
            f"Creates a project directory with {PROJECT_MARKER} metadata and starter "
            "folders (docs, src, data). Mutating operation requires confirm=true."
        ),
        parameters=[
            ToolParameter(
                name="name",
                type="string",
                description="Human-readable project name to store in the marker file.",
            ),
            ToolParameter(
                name="path",
                type="string",
                description="Project directory path relative to the goblin workspace root.",
            ),
            ToolParameter(
                name="template",
                type="string",
                description="Optional template label stored in project metadata.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="confirm",
                type="boolean",
                description="Safety confirmation. Must be true to create a project.",
            ),
        ],
        handler=_handle_create_project,
        category="projects",
    )
)

register_tool(
    ToolDefinition(
        name="list_projects",
        description=(
            "Use when the user wants to discover projects in the workspace. "
            f"Finds directories containing {PROJECT_MARKER} and returns summaries."
        ),
        parameters=[
            ToolParameter(
                name="directory",
                type="string",
                description="Directory to scan, relative to the goblin workspace root.",
                required=False,
                default=".",
            ),
            ToolParameter(
                name="max_depth",
                type="integer",
                description="Maximum directory depth to scan from the provided root.",
                required=False,
                default=4,
            ),
        ],
        handler=_handle_list_projects,
        category="projects",
    )
)

register_tool(
    ToolDefinition(
        name="get_project_info",
        description=(
            "Use when the user wants detailed project metadata and structure stats "
            "for a specific project directory."
        ),
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="Project directory path relative to the goblin workspace root.",
            ),
        ],
        handler=_handle_get_project_info,
        category="projects",
    )
)
