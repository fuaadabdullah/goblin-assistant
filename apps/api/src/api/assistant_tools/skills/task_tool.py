"""
Task tools for Goblin Assistant.

Provides lightweight task management (create/list/update/complete) using
the existing TaskStore persistence abstraction.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from api.storage.tasks import task_store

from ..registry import ToolDefinition, ToolParameter, register_tool

TASK_TYPE = "assistant_task"
ALLOWED_STATUS = {"pending", "in_progress", "completed"}
ALLOWED_PRIORITY = {"low", "medium", "high"}


def _normalize_task(task: Dict[str, Any]) -> Dict[str, Any]:
    payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
    return {
        "task_id": task.get("task_id"),
        "title": payload.get("title", ""),
        "details": payload.get("details", ""),
        "priority": payload.get("priority", "medium"),
        "due_date": payload.get("due_date"),
        "project_path": payload.get("project_path"),
        "tags": payload.get("tags", []),
        "status": task.get("status", "pending"),
        "created_at": task.get("created_at"),
        "updated_at": task.get("updated_at"),
        "completion_note": (task.get("result") or {}).get("completion_note"),
    }


async def _handle_create_task(
    title: str,
    details: Optional[str] = None,
    priority: str = "medium",
    due_date: Optional[str] = None,
    project_path: Optional[str] = None,
    tags: Optional[List[str]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    if priority not in ALLOWED_PRIORITY:
        return {"error": f"Invalid priority: {priority}. Allowed: {sorted(ALLOWED_PRIORITY)}"}
    if not title.strip():
        return {"error": "title must be non-empty"}

    task_id = str(uuid.uuid4())
    payload = {
        "title": title.strip(),
        "details": (details or "").strip(),
        "priority": priority,
        "due_date": due_date,
        "project_path": project_path,
        "tags": tags or [],
    }

    task_data = {
        "task_id": task_id,
        "user_id": user_id,
        "status": "pending",
        "task_type": TASK_TYPE,
        "payload": payload,
        "result": None,
        "metadata": {"source": "assistant_tools"},
    }
    await task_store.save_task(task_id, task_data)
    created = await task_store.get_task(task_id)
    if not created:
        return {"error": "Failed to persist created task"}
    return {"created": True, "task": _normalize_task(created)}


async def _handle_list_tasks(
    status: Optional[str] = None,
    limit: int = 50,
    project_path: Optional[str] = None,
    tag: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    if status is not None and status not in ALLOWED_STATUS:
        return {"error": f"Invalid status: {status}. Allowed: {sorted(ALLOWED_STATUS)}"}

    capped_limit = max(1, min(limit, 200))
    raw_tasks = await task_store.list_tasks(status=status, limit=capped_limit * 4)
    filtered: List[Dict[str, Any]] = []
    for task in raw_tasks:
        if task.get("task_type") != TASK_TYPE:
            continue
        if user_id and task.get("user_id") not in (None, user_id):
            continue
        payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
        if project_path and payload.get("project_path") != project_path:
            continue
        tags = payload.get("tags") if isinstance(payload.get("tags"), list) else []
        if tag and tag not in tags:
            continue
        filtered.append(_normalize_task(task))
        if len(filtered) >= capped_limit:
            break

    return {"tasks": filtered, "count": len(filtered)}


async def _handle_update_task(
    task_id: str,
    title: Optional[str] = None,
    details: Optional[str] = None,
    priority: Optional[str] = None,
    due_date: Optional[str] = None,
    tags: Optional[List[str]] = None,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    existing = await task_store.get_task(task_id)
    if not existing:
        return {"error": f"Task not found: {task_id}"}
    if existing.get("task_type") != TASK_TYPE:
        return {"error": f"Task is not managed by assistant tools: {task_id}"}
    if user_id and existing.get("user_id") not in (None, user_id):
        return {"error": f"Task not accessible for current user: {task_id}"}

    payload = dict(existing.get("payload") or {})
    if title is not None:
        if not title.strip():
            return {"error": "title must be non-empty when provided"}
        payload["title"] = title.strip()
    if details is not None:
        payload["details"] = details.strip()
    if priority is not None:
        if priority not in ALLOWED_PRIORITY:
            return {"error": f"Invalid priority: {priority}. Allowed: {sorted(ALLOWED_PRIORITY)}"}
        payload["priority"] = priority
    if due_date is not None:
        payload["due_date"] = due_date
    if tags is not None:
        payload["tags"] = tags

    if status is not None and status not in ALLOWED_STATUS:
        return {"error": f"Invalid status: {status}. Allowed: {sorted(ALLOWED_STATUS)}"}

    existing["payload"] = payload
    if status is not None:
        existing["status"] = status
    existing["updated_at"] = datetime.utcnow().isoformat()

    await task_store.save_task(task_id, existing)
    updated = await task_store.get_task(task_id)
    if not updated:
        return {"error": f"Failed to load updated task: {task_id}"}
    return {"updated": True, "task": _normalize_task(updated)}


async def _handle_complete_task(
    task_id: str,
    completion_note: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    existing = await task_store.get_task(task_id)
    if not existing:
        return {"error": f"Task not found: {task_id}"}
    if existing.get("task_type") != TASK_TYPE:
        return {"error": f"Task is not managed by assistant tools: {task_id}"}
    if user_id and existing.get("user_id") not in (None, user_id):
        return {"error": f"Task not accessible for current user: {task_id}"}

    existing["status"] = "completed"
    existing["result"] = {"completion_note": completion_note or ""}
    await task_store.save_task(task_id, existing)
    completed = await task_store.get_task(task_id)
    if not completed:
        return {"error": f"Failed to load completed task: {task_id}"}
    return {"completed": True, "task": _normalize_task(completed)}


register_tool(
    ToolDefinition(
        name="create_task",
        description=(
            "Use when the user wants to create a new actionable task. "
            "Returns a stable task_id and task summary."
        ),
        parameters=[
            ToolParameter(name="title", type="string", description="Short task title."),
            ToolParameter(
                name="details",
                type="string",
                description="Optional task details.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="priority",
                type="string",
                description="Task priority: low, medium, or high.",
                required=False,
                enum=["low", "medium", "high"],
                default="medium",
            ),
            ToolParameter(
                name="due_date",
                type="string",
                description="Optional due date text or ISO timestamp.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="project_path",
                type="string",
                description="Optional related project path.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="tags",
                type="array",
                description="Optional string tags.",
                required=False,
                default=[],
                items={"type": "string"},
            ),
        ],
        handler=_handle_create_task,
        category="tasks",
    )
)

register_tool(
    ToolDefinition(
        name="list_tasks",
        description=(
            "Use when the user wants to view assistant-managed tasks, optionally "
            "filtered by status, project path, or tag."
        ),
        parameters=[
            ToolParameter(
                name="status",
                type="string",
                description="Optional status filter: pending, in_progress, completed.",
                required=False,
                enum=["pending", "in_progress", "completed"],
                default=None,
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="Maximum tasks to return (1-200). Defaults to 50.",
                required=False,
                default=50,
            ),
            ToolParameter(
                name="project_path",
                type="string",
                description="Optional project path filter.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="tag",
                type="string",
                description="Optional tag filter.",
                required=False,
                default=None,
            ),
        ],
        handler=_handle_list_tasks,
        category="tasks",
    )
)

register_tool(
    ToolDefinition(
        name="update_task",
        description=(
            "Use when the user wants to modify an existing assistant task. "
            "Supports partial field updates and optional status transitions."
        ),
        parameters=[
            ToolParameter(name="task_id", type="string", description="Task ID to update."),
            ToolParameter(
                name="title",
                type="string",
                description="Optional new title.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="details",
                type="string",
                description="Optional new details.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="priority",
                type="string",
                description="Optional priority update.",
                required=False,
                enum=["low", "medium", "high"],
                default=None,
            ),
            ToolParameter(
                name="due_date",
                type="string",
                description="Optional due date update.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="tags",
                type="array",
                description="Optional full tag replacement.",
                required=False,
                default=None,
                items={"type": "string"},
            ),
            ToolParameter(
                name="status",
                type="string",
                description="Optional status transition.",
                required=False,
                enum=["pending", "in_progress", "completed"],
                default=None,
            ),
        ],
        handler=_handle_update_task,
        category="tasks",
    )
)

register_tool(
    ToolDefinition(
        name="complete_task",
        description=(
            "Use when the user marks a task complete. Sets status to completed "
            "and optionally stores a completion note."
        ),
        parameters=[
            ToolParameter(name="task_id", type="string", description="Task ID to complete."),
            ToolParameter(
                name="completion_note",
                type="string",
                description="Optional completion note.",
                required=False,
                default=None,
            ),
        ],
        handler=_handle_complete_task,
        category="tasks",
    )
)
