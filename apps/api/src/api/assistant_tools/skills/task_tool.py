"""Task and scheduling tools for Goblin Assistant."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...services.scheduling_service import scheduling_provider
from ..registry import ToolDefinition, ToolParameter, register_tool

TASK_TYPE = "assistant_task"
ALLOWED_STATUS = {"pending", "in_progress", "completed"}
ALLOWED_PRIORITY = {"low", "medium", "high"}


async def _handle_create_task(
    title: str,
    details: Optional[str] = None,
    priority: str = "medium",
    due_date: Optional[str] = None,
    project_path: Optional[str] = None,
    tags: Optional[List[str]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    return await scheduling_provider.create_task(
        title=title,
        details=details,
        priority=priority,
        due_at=due_date,
        project_path=project_path,
        tags=tags,
        user_id=user_id,
    )


async def _handle_list_tasks(
    status: Optional[str] = None,
    limit: int = 50,
    project_path: Optional[str] = None,
    tag: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    return await scheduling_provider.list_tasks(
        status=status,
        limit=limit,
        project_path=project_path,
        tag=tag,
        user_id=user_id,
    )


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
    return await scheduling_provider.update_task(
        task_id=task_id,
        title=title,
        details=details,
        priority=priority,
        due_at=due_date,
        tags=tags,
        status=status,
        user_id=user_id,
    )


async def _handle_complete_task(
    task_id: str,
    completion_note: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    return await scheduling_provider.complete_task(
        task_id=task_id,
        completion_note=completion_note,
        user_id=user_id,
    )


async def _handle_create_reminder(
    title: str,
    trigger_at: str,
    note: Optional[str] = None,
    task_id: Optional[str] = None,
    status: str = "scheduled",
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    return await scheduling_provider.create_reminder(
        title=title,
        trigger_at=trigger_at,
        note=note,
        task_id=task_id,
        status=status,
        user_id=user_id,
    )


async def _handle_list_reminders(
    status: Optional[str] = None,
    limit: int = 50,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    return await scheduling_provider.list_reminders(
        status=status,
        limit=limit,
        user_id=user_id,
    )


async def _handle_create_calendar_event(
    title: str,
    start_time: str,
    end_time: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    status: str = "planned",
    task_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    return await scheduling_provider.create_calendar_event(
        title=title,
        start_time=start_time,
        end_time=end_time,
        description=description,
        location=location,
        notes=notes,
        attendees=attendees,
        status=status,
        task_id=task_id,
        user_id=user_id,
    )


async def _handle_list_calendar_events(
    status: Optional[str] = None,
    limit: int = 50,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    return await scheduling_provider.list_calendar_events(
        status=status,
        limit=limit,
        user_id=user_id,
    )


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
            "Use when the user wants to update an existing assistant-managed task "
            "without completing it."
        ),
        parameters=[
            ToolParameter(name="task_id", type="string", description="Task identifier."),
            ToolParameter(
                name="title",
                type="string",
                description="Optional new task title.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="details",
                type="string",
                description="Optional updated details.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="priority",
                type="string",
                description="Optional priority update: low, medium, or high.",
                required=False,
                enum=["low", "medium", "high"],
                default=None,
            ),
            ToolParameter(
                name="due_date",
                type="string",
                description="Optional due date text or ISO timestamp.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="tags",
                type="array",
                description="Optional replacement tags.",
                required=False,
                default=None,
                items={"type": "string"},
            ),
            ToolParameter(
                name="status",
                type="string",
                description="Optional status update.",
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
        description=("Use when the user wants to mark an assistant-managed task as completed."),
        parameters=[
            ToolParameter(name="task_id", type="string", description="Task identifier."),
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

register_tool(
    ToolDefinition(
        name="create_reminder",
        description=("Use when the user wants to schedule a reminder tied to a task or date."),
        parameters=[
            ToolParameter(name="title", type="string", description="Reminder title."),
            ToolParameter(
                name="trigger_at",
                type="string",
                description="Reminder trigger time as text or ISO timestamp.",
            ),
            ToolParameter(
                name="note",
                type="string",
                description="Optional reminder note.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="task_id",
                type="string",
                description="Optional linked task identifier.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="status",
                type="string",
                description="Reminder status: scheduled, triggered, dismissed, or cancelled.",
                required=False,
                enum=["scheduled", "triggered", "dismissed", "cancelled"],
                default="scheduled",
            ),
        ],
        handler=_handle_create_reminder,
        category="tasks",
    )
)

register_tool(
    ToolDefinition(
        name="list_reminders",
        description="Use when the user wants to view assistant-managed reminders.",
        parameters=[
            ToolParameter(
                name="status",
                type="string",
                description="Optional reminder status filter.",
                required=False,
                enum=["scheduled", "triggered", "dismissed", "cancelled"],
                default=None,
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="Maximum reminders to return (1-200). Defaults to 50.",
                required=False,
                default=50,
            ),
        ],
        handler=_handle_list_reminders,
        category="tasks",
    )
)

register_tool(
    ToolDefinition(
        name="create_calendar_event",
        description=(
            "Use when the user wants to draft or store a calendar event in the scheduling layer."
        ),
        parameters=[
            ToolParameter(name="title", type="string", description="Event title."),
            ToolParameter(
                name="start_time",
                type="string",
                description="Event start time as text or ISO timestamp.",
            ),
            ToolParameter(
                name="end_time",
                type="string",
                description="Optional event end time.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="description",
                type="string",
                description="Optional event description.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="location",
                type="string",
                description="Optional event location.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="notes",
                type="string",
                description="Optional event notes.",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="attendees",
                type="array",
                description="Optional list of attendee names or emails.",
                required=False,
                default=None,
                items={"type": "string"},
            ),
            ToolParameter(
                name="status",
                type="string",
                description="Event status: planned, confirmed, cancelled, completed.",
                required=False,
                enum=["planned", "confirmed", "cancelled", "completed"],
                default="planned",
            ),
        ],
        handler=_handle_create_calendar_event,
        category="tasks",
    )
)

register_tool(
    ToolDefinition(
        name="list_calendar_events",
        description="Use when the user wants to view assistant-managed calendar events.",
        parameters=[
            ToolParameter(
                name="status",
                type="string",
                description="Optional event status filter.",
                required=False,
                enum=["planned", "confirmed", "cancelled", "completed"],
                default=None,
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="Maximum events to return (1-200). Defaults to 50.",
                required=False,
                default=50,
            ),
        ],
        handler=_handle_list_calendar_events,
        category="tasks",
    )
)
