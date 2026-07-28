"""Scheduling provider abstraction for assistant task, reminder, and calendar data."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol

from api.storage.tasks import task_store

TASK_TYPE = "assistant_task"
REMINDER_TYPE = "assistant_reminder"
CALENDAR_EVENT_TYPE = "assistant_calendar_event"

ALLOWED_STATUS = {"pending", "in_progress", "completed"}
ALLOWED_PRIORITY = {"low", "medium", "high"}
REMINDER_STATUS = {"scheduled", "triggered", "dismissed", "cancelled"}
CALENDAR_EVENT_STATUS = {"planned", "confirmed", "cancelled", "completed"}


def _utc_now() -> str:
    return datetime.utcnow().isoformat()


def _normalize_tags(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _normalize_priority(priority: Optional[str]) -> str:
    candidate = (priority or "medium").strip().lower()
    return candidate if candidate in ALLOWED_PRIORITY else "medium"


def _normalize_due(value: Optional[str], fallback: Optional[str] = None) -> Optional[str]:
    candidate = (value or fallback or "").strip()
    return candidate or None


def _normalize_status(status: Optional[str], allowed: set[str], default: str) -> str:
    candidate = (status or default).strip().lower()
    return candidate if candidate in allowed else default


def _normalize_task(task: Dict[str, Any]) -> Dict[str, Any]:
    payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
    due_at = _normalize_due(payload.get("due_at"), payload.get("due_date"))
    return {
        "task_id": task.get("task_id"),
        "title": payload.get("title", ""),
        "details": payload.get("details", ""),
        "priority": _normalize_priority(payload.get("priority")),
        "due_at": due_at,
        "due_date": due_at,
        "project_path": payload.get("project_path"),
        "tags": _normalize_tags(payload.get("tags")),
        "status": task.get("status", "pending"),
        "created_at": task.get("created_at"),
        "updated_at": task.get("updated_at"),
        "completion_note": (task.get("result") or {}).get("completion_note"),
    }


def _normalize_reminder(task: Dict[str, Any]) -> Dict[str, Any]:
    payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
    trigger_at = _normalize_due(payload.get("trigger_at"), payload.get("due_at"))
    return {
        "reminder_id": task.get("task_id"),
        "title": payload.get("title", ""),
        "note": payload.get("note", ""),
        "trigger_at": trigger_at,
        "task_id": payload.get("task_id"),
        "status": _normalize_status(task.get("status"), REMINDER_STATUS, "scheduled"),
        "created_at": task.get("created_at"),
        "updated_at": task.get("updated_at"),
    }


def _normalize_calendar_event(task: Dict[str, Any]) -> Dict[str, Any]:
    payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
    return {
        "event_id": task.get("task_id"),
        "title": payload.get("title", ""),
        "description": payload.get("description", ""),
        "start_time": _normalize_due(payload.get("start_time")),
        "end_time": _normalize_due(payload.get("end_time")),
        "location": payload.get("location"),
        "notes": payload.get("notes"),
        "task_id": payload.get("task_id"),
        "attendees": _normalize_tags(payload.get("attendees")),
        "status": _normalize_status(task.get("status"), CALENDAR_EVENT_STATUS, "planned"),
        "created_at": task.get("created_at"),
        "updated_at": task.get("updated_at"),
    }


class SchedulingProvider(Protocol):
    async def create_task(
        self,
        *,
        title: str,
        details: Optional[str] = None,
        priority: str = "medium",
        due_at: Optional[str] = None,
        project_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    async def list_tasks(
        self,
        *,
        status: Optional[str] = None,
        limit: int = 50,
        project_path: Optional[str] = None,
        tag: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    async def update_task(
        self,
        *,
        task_id: str,
        title: Optional[str] = None,
        details: Optional[str] = None,
        priority: Optional[str] = None,
        due_at: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    async def complete_task(
        self,
        *,
        task_id: str,
        completion_note: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    async def create_reminder(
        self,
        *,
        title: str,
        trigger_at: str,
        note: Optional[str] = None,
        task_id: Optional[str] = None,
        status: str = "scheduled",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    async def list_reminders(
        self,
        *,
        status: Optional[str] = None,
        limit: int = 50,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    async def create_calendar_event(
        self,
        *,
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
    ) -> Dict[str, Any]: ...

    async def list_calendar_events(
        self,
        *,
        status: Optional[str] = None,
        limit: int = 50,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...


@dataclass
class LocalSchedulingProvider:
    """Persistence-backed scheduling provider using the existing task store."""

    task_store_ref: Any = task_store
    task_type: str = TASK_TYPE
    reminder_type: str = REMINDER_TYPE
    calendar_event_type: str = CALENDAR_EVENT_TYPE
    _reserved_types: set[str] = field(
        default_factory=lambda: {TASK_TYPE, REMINDER_TYPE, CALENDAR_EVENT_TYPE}
    )

    async def _save_record(self, record_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        await self.task_store_ref.save_task(record_id, task_data)
        loaded = await self.task_store_ref.get_task(record_id)
        return loaded or task_data

    async def _list_records(
        self,
        *,
        record_type: str,
        status: Optional[str],
        limit: int,
        user_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        raw_items = await self.task_store_ref.list_tasks(status=status, limit=max(limit * 4, 100))
        results: List[Dict[str, Any]] = []
        for item in raw_items:
            if item.get("task_type") != record_type:
                continue
            if user_id and item.get("user_id") not in (None, user_id):
                continue
            results.append(item)
            if len(results) >= limit:
                break
        return results

    async def create_task(
        self,
        *,
        title: str,
        details: Optional[str] = None,
        priority: str = "medium",
        due_at: Optional[str] = None,
        project_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not title.strip():
            return {"error": "title must be non-empty"}
        normalized_priority = _normalize_priority(priority)
        task_id = str(uuid.uuid4())
        normalized_due = _normalize_due(due_at)
        payload = {
            "title": title.strip(),
            "details": (details or "").strip(),
            "priority": normalized_priority,
            "due_at": normalized_due,
            "due_date": normalized_due,
            "project_path": project_path,
            "tags": _normalize_tags(tags),
        }
        task_data = {
            "task_id": task_id,
            "user_id": user_id,
            "status": "pending",
            "task_type": self.task_type,
            "payload": payload,
            "result": None,
            "metadata": {"source": "assistant_tools"},
        }
        created = await self._save_record(task_id, task_data)
        return {"created": True, "task": _normalize_task(created)}

    async def list_tasks(
        self,
        *,
        status: Optional[str] = None,
        limit: int = 50,
        project_path: Optional[str] = None,
        tag: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if status is not None and status not in ALLOWED_STATUS:
            return {"error": f"Invalid status: {status}. Allowed: {sorted(ALLOWED_STATUS)}"}
        capped_limit = max(1, min(limit, 200))
        raw_tasks = await self._list_records(
            record_type=self.task_type,
            status=status,
            limit=capped_limit,
            user_id=user_id,
        )
        filtered: List[Dict[str, Any]] = []
        for task in raw_tasks:
            payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
            if project_path and payload.get("project_path") != project_path:
                continue
            tags = payload.get("tags") if isinstance(payload.get("tags"), list) else []
            if tag and tag not in tags:
                continue
            filtered.append(_normalize_task(task))
        return {"tasks": filtered, "count": len(filtered)}

    async def update_task(
        self,
        *,
        task_id: str,
        title: Optional[str] = None,
        details: Optional[str] = None,
        priority: Optional[str] = None,
        due_at: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        existing = await self.task_store_ref.get_task(task_id)
        if not existing:
            return {"error": f"Task not found: {task_id}"}
        if existing.get("task_type") != self.task_type:
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
                return {
                    "error": f"Invalid priority: {priority}. Allowed: {sorted(ALLOWED_PRIORITY)}"
                }
            payload["priority"] = priority
        if due_at is not None:
            normalized_due = _normalize_due(due_at)
            payload["due_at"] = normalized_due
            payload["due_date"] = normalized_due
        if tags is not None:
            payload["tags"] = _normalize_tags(tags)

        if status is not None and status not in ALLOWED_STATUS:
            return {"error": f"Invalid status: {status}. Allowed: {sorted(ALLOWED_STATUS)}"}

        existing["payload"] = payload
        if status is not None:
            existing["status"] = status
        existing["updated_at"] = _utc_now()
        updated = await self._save_record(task_id, existing)
        return {"updated": True, "task": _normalize_task(updated)}

    async def complete_task(
        self,
        *,
        task_id: str,
        completion_note: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        existing = await self.task_store_ref.get_task(task_id)
        if not existing:
            return {"error": f"Task not found: {task_id}"}
        if existing.get("task_type") != self.task_type:
            return {"error": f"Task is not managed by assistant tools: {task_id}"}
        if user_id and existing.get("user_id") not in (None, user_id):
            return {"error": f"Task not accessible for current user: {task_id}"}

        existing["status"] = "completed"
        existing["result"] = {"completion_note": completion_note or ""}
        completed = await self._save_record(task_id, existing)
        return {"completed": True, "task": _normalize_task(completed)}

    async def create_reminder(
        self,
        *,
        title: str,
        trigger_at: str,
        note: Optional[str] = None,
        task_id: Optional[str] = None,
        status: str = "scheduled",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not title.strip():
            return {"error": "title must be non-empty"}
        if not trigger_at.strip():
            return {"error": "trigger_at must be provided"}
        normalized_status = _normalize_status(status, REMINDER_STATUS, "scheduled")
        reminder_id = str(uuid.uuid4())
        task_data = {
            "task_id": reminder_id,
            "user_id": user_id,
            "status": normalized_status,
            "task_type": self.reminder_type,
            "payload": {
                "title": title.strip(),
                "note": (note or "").strip(),
                "trigger_at": trigger_at.strip(),
                "task_id": task_id,
            },
            "result": None,
            "metadata": {"source": "assistant_tools"},
        }
        created = await self._save_record(reminder_id, task_data)
        return {"created": True, "reminder": _normalize_reminder(created)}

    async def list_reminders(
        self,
        *,
        status: Optional[str] = None,
        limit: int = 50,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if status is not None and status not in REMINDER_STATUS:
            return {"error": f"Invalid status: {status}. Allowed: {sorted(REMINDER_STATUS)}"}
        capped_limit = max(1, min(limit, 200))
        raw_items = await self._list_records(
            record_type=self.reminder_type,
            status=status,
            limit=capped_limit,
            user_id=user_id,
        )
        reminders = [_normalize_reminder(item) for item in raw_items]
        return {"reminders": reminders, "count": len(reminders)}

    async def create_calendar_event(
        self,
        *,
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
        if not title.strip():
            return {"error": "title must be non-empty"}
        if not start_time.strip():
            return {"error": "start_time must be provided"}
        normalized_status = _normalize_status(status, CALENDAR_EVENT_STATUS, "planned")
        event_id = str(uuid.uuid4())
        task_data = {
            "task_id": event_id,
            "user_id": user_id,
            "status": normalized_status,
            "task_type": self.calendar_event_type,
            "payload": {
                "title": title.strip(),
                "description": (description or "").strip(),
                "start_time": start_time.strip(),
                "end_time": _normalize_due(end_time),
                "location": location,
                "notes": notes,
                "attendees": _normalize_tags(attendees),
                "task_id": task_id,
            },
            "result": None,
            "metadata": {"source": "assistant_tools"},
        }
        created = await self._save_record(event_id, task_data)
        return {"created": True, "event": _normalize_calendar_event(created)}

    async def list_calendar_events(
        self,
        *,
        status: Optional[str] = None,
        limit: int = 50,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if status is not None and status not in CALENDAR_EVENT_STATUS:
            return {"error": f"Invalid status: {status}. Allowed: {sorted(CALENDAR_EVENT_STATUS)}"}
        capped_limit = max(1, min(limit, 200))
        raw_items = await self._list_records(
            record_type=self.calendar_event_type,
            status=status,
            limit=capped_limit,
            user_id=user_id,
        )
        events = [_normalize_calendar_event(item) for item in raw_items]
        return {"events": events, "count": len(events)}


scheduling_provider: SchedulingProvider = LocalSchedulingProvider()
