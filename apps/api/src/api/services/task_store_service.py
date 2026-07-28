"""Route-safe accessors for task persistence."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from api.storage import conversation_store  # noqa: F401 - compatibility alias
from api.storage.tasks import TaskStore
from api.storage.tasks import get_task_store as _get_task_store


async def get_task_store() -> TaskStore:
    return await _get_task_store()


async def save_task(task_id: str, task_data: Dict[str, Any]) -> None:
    store = await get_task_store()
    await store.save_task(task_id, task_data)


async def load_task(task_id: str) -> Optional[Dict[str, Any]]:
    store = await get_task_store()
    return await store.get_task(task_id)


async def list_tasks(status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    store = await get_task_store()
    return await store.list_tasks(status=status, limit=limit)


async def update_task_status(
    task_id: str,
    status: str,
    result: Optional[Dict[str, Any]] = None,
) -> bool:
    store = await get_task_store()
    return await store.update_task_status(task_id, status, result=result)
