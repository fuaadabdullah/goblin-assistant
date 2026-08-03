"""
Persistent storage wrapper for tasks with database, Redis, and explicit memory backends.
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

import structlog

from ..core.redis_client import get_redis_client

_log = structlog.get_logger()

TaskStoreBackend = Literal["database", "redis", "memory"]
TASK_INDEX_KEY = "task_store:index"
TASK_KEY_PREFIX = "task_store:task:"


def _is_true(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _task_key(task_id: str) -> str:
    return f"{TASK_KEY_PREFIX}{task_id}"


def _timestamp_score(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            normalized = value.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized).timestamp()
        except ValueError:
            return time.time()
    return time.time()


def _decode_task(raw: Any) -> Optional[Dict[str, Any]]:
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if not isinstance(raw, str):
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _resolve_backend(explicit_backend: Optional[TaskStoreBackend]) -> TaskStoreBackend:
    if explicit_backend:
        return explicit_backend
    env_backend = os.getenv("TASK_STORE_BACKEND", "").strip().lower()
    if env_backend in {"database", "redis", "memory"}:
        return env_backend  # type: ignore[return-value]
    if _is_true(os.getenv("USE_DATABASE")):
        return "database"
    return "redis"


def _default_allow_memory_fallback() -> bool:
    explicit = os.getenv("TASK_STORE_ALLOW_INMEMORY_FALLBACK")
    if explicit is not None:
        return _is_true(explicit)
    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    return bool(os.getenv("PYTEST_CURRENT_TEST")) or environment != "production"


class TaskStore:
    """Storage abstraction for task data.

    Redis is the default runtime backend. Database mode remains available for
    installations that explicitly opt into it, and memory mode is reserved for
    tests or local fallback when Redis is unavailable outside production.
    """

    def __init__(
        self,
        *,
        backend: Optional[TaskStoreBackend] = None,
        allow_memory_fallback: Optional[bool] = None,
    ) -> None:
        self._backend = _resolve_backend(backend)
        self.use_db = self._backend == "database"
        self._allow_memory_fallback = (
            _default_allow_memory_fallback()
            if allow_memory_fallback is None
            else allow_memory_fallback
        )
        self._redis_available: Optional[bool] = None
        self._in_memory_tasks: Dict[str, Dict[str, Any]] = {}

    def _init_db(self):
        """Compatibility no-op for tests that patch the previous startup ping."""

    def _active_backend(self) -> TaskStoreBackend:
        if getattr(self, "use_db", False):
            return "database"
        backend = getattr(self, "_backend", None)
        if backend in {"database", "redis", "memory"}:
            return backend
        return "memory"

    def _fallback_allowed(self) -> bool:
        return bool(getattr(self, "_allow_memory_fallback", True))

    async def _get_redis(self):
        return await get_redis_client()

    async def _with_redis_or_memory(self, operation: str, redis_call, memory_call):
        try:
            redis = await self._get_redis()
            self._redis_available = True
            return await redis_call(redis)
        except Exception as exc:
            self._redis_available = False
            if not self._fallback_allowed():
                _log.error("task_store_redis_unavailable", operation=operation, error=str(exc))
                raise RuntimeError("task store Redis backend is unavailable") from exc
            _log.warning(
                "task_store_using_memory_fallback",
                operation=operation,
                error=str(exc),
            )
            return await memory_call()

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a task by ID."""
        backend = self._active_backend()
        if backend == "database":
            return await self._get_task_from_db(task_id)
        if backend == "memory":
            return self._in_memory_tasks.get(task_id)
        return await self._with_redis_or_memory(
            "get",
            lambda redis: self._get_task_from_redis(redis, task_id),
            lambda: self._get_task_from_memory(task_id),
        )

    async def save_task(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """Save or update a task."""
        # Add timestamps
        now = _now_iso()
        if "created_at" not in task_data:
            task_data["created_at"] = now
        task_data["updated_at"] = now
        task_data.setdefault("task_id", task_id)

        backend = self._active_backend()
        if backend == "database":
            await self._save_task_to_db(task_id, task_data)
        elif backend == "memory":
            await self._save_task_to_memory(task_id, task_data)
        else:
            await self._with_redis_or_memory(
                "save",
                lambda redis: self._save_task_to_redis(redis, task_id, task_data),
                lambda: self._save_task_to_memory(task_id, task_data),
            )

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID. Returns True if task was found and deleted."""
        backend = self._active_backend()
        if backend == "database":
            return await self._delete_task_from_db(task_id)
        if backend == "memory":
            return await self._delete_task_from_memory(task_id)
        return await self._with_redis_or_memory(
            "delete",
            lambda redis: self._delete_task_from_redis(redis, task_id),
            lambda: self._delete_task_from_memory(task_id),
        )

    async def list_tasks(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List tasks, optionally filtered by status."""
        backend = self._active_backend()
        if backend == "database":
            return await self._list_tasks_from_db(status, limit)
        if backend == "memory":
            return await self._list_tasks_from_memory(status, limit)
        return await self._with_redis_or_memory(
            "list",
            lambda redis: self._list_tasks_from_redis(redis, status, limit),
            lambda: self._list_tasks_from_memory(status, limit),
        )

    async def update_task_status(
        self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update task status and optionally set result. Returns True if task was found."""
        task = await self.get_task(task_id)
        if not task:
            return False

        task["status"] = status
        task["updated_at"] = datetime.utcnow().isoformat()

        if result is not None:
            task["result"] = result

        await self.save_task(task_id, task)
        return True

    async def _get_task_from_memory(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._in_memory_tasks.get(task_id)

    async def _save_task_to_memory(self, task_id: str, task_data: Dict[str, Any]) -> None:
        self._in_memory_tasks[task_id] = dict(task_data)

    async def _delete_task_from_memory(self, task_id: str) -> bool:
        return self._in_memory_tasks.pop(task_id, None) is not None

    async def _list_tasks_from_memory(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        tasks = list(self._in_memory_tasks.values())
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        tasks.sort(key=lambda task: _timestamp_score(task.get("created_at")))
        return tasks[-limit:]

    async def _get_task_from_redis(self, redis, task_id: str) -> Optional[Dict[str, Any]]:
        return _decode_task(await redis.get(_task_key(task_id)))

    async def _save_task_to_redis(
        self,
        redis,
        task_id: str,
        task_data: Dict[str, Any],
    ) -> None:
        payload = json.dumps(task_data, default=str)
        score = _timestamp_score(task_data.get("created_at"))
        pipe = redis.pipeline()
        pipe.set(_task_key(task_id), payload)
        pipe.zadd(TASK_INDEX_KEY, {task_id: score})
        await pipe.execute()

    async def _delete_task_from_redis(self, redis, task_id: str) -> bool:
        pipe = redis.pipeline()
        pipe.delete(_task_key(task_id))
        pipe.zrem(TASK_INDEX_KEY, task_id)
        deleted, _ = await pipe.execute()
        return int(deleted or 0) > 0

    async def _list_tasks_from_redis(
        self,
        redis,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        requested = max(limit, 1)
        scan_count = requested if status is None else max(requested * 4, 100)
        task_ids = await redis.zrevrange(TASK_INDEX_KEY, 0, scan_count - 1)
        tasks: List[Dict[str, Any]] = []
        stale_ids: List[str] = []
        for raw_id in task_ids:
            task_id = raw_id.decode("utf-8") if isinstance(raw_id, bytes) else str(raw_id)
            task = await self._get_task_from_redis(redis, task_id)
            if task is None:
                stale_ids.append(task_id)
                continue
            if status and task.get("status") != status:
                continue
            tasks.append(task)
            if len(tasks) >= requested:
                break
        if stale_ids:
            await redis.zrem(TASK_INDEX_KEY, *stale_ids)
        return tasks

    # Database implementation methods
    async def _get_task_from_db(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve task from database."""
        try:
            from sqlalchemy import select

            from .database import get_db_context
            from .models import TaskModel

            async with get_db_context() as session:
                result = await session.execute(
                    select(TaskModel).where(TaskModel.task_id == task_id)
                )
                task = result.scalar_one_or_none()
                if task:
                    return {
                        "task_id": task.task_id,
                        "user_id": task.user_id,
                        "status": task.status,
                        "task_type": task.task_type,
                        "payload": task.payload,
                        "result": task.result,
                        "created_at": task.created_at.isoformat(),
                        "updated_at": task.updated_at.isoformat(),
                        "metadata": task.metadata_,
                    }
                return None
        except Exception as e:
            _log.error("task_db_get_failed", task_id=task_id, error=str(e))
            return None

    async def _save_task_to_db(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """Save task to database."""
        try:
            from sqlalchemy import select

            from .database import get_db_context
            from .models import TaskModel

            async with get_db_context() as session:
                # Check if task exists
                result = await session.execute(
                    select(TaskModel).where(TaskModel.task_id == task_id)
                )
                task = result.scalar_one_or_none()

                if task:
                    # Update existing task
                    task.status = task_data.get("status", task.status)
                    task.task_type = task_data.get("task_type", task.task_type)
                    task.payload = task_data.get("payload", task.payload)
                    task.result = task_data.get("result", task.result)
                    task.updated_at = datetime.utcnow()
                    task.metadata_ = task_data.get("metadata", task.metadata_)
                else:
                    # Create new task
                    task = TaskModel(
                        task_id=task_id,
                        user_id=task_data.get("user_id"),
                        status=task_data.get("status", "pending"),
                        task_type=task_data.get("task_type"),
                        payload=task_data.get("payload", {}),
                        result=task_data.get("result"),
                        created_at=(
                            datetime.fromisoformat(task_data["created_at"])
                            if "created_at" in task_data
                            else datetime.utcnow()
                        ),
                        updated_at=(
                            datetime.fromisoformat(task_data["updated_at"])
                            if "updated_at" in task_data
                            else datetime.utcnow()
                        ),
                        metadata_=task_data.get("metadata", {}),
                    )
                    session.add(task)
        except Exception as e:
            _log.error("task_db_save_failed", task_id=task_id, error=str(e))

    async def _delete_task_from_db(self, task_id: str) -> bool:
        """Delete task from database."""
        try:
            from sqlalchemy import delete

            from .database import get_db_context
            from .models import TaskModel

            async with get_db_context() as session:
                result = await session.execute(
                    delete(TaskModel).where(TaskModel.task_id == task_id)
                )
                return result.rowcount > 0
        except Exception as e:
            _log.error("task_db_delete_failed", task_id=task_id, error=str(e))
            return False

    async def _list_tasks_from_db(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List tasks from database."""
        try:
            from sqlalchemy import desc, select

            from .database import get_db_context
            from .models import TaskModel

            async with get_db_context() as session:
                query = select(TaskModel).order_by(desc(TaskModel.created_at)).limit(limit)
                if status:
                    query = query.where(TaskModel.status == status)
                result = await session.execute(query)
                tasks = result.scalars().all()
                return [
                    {
                        "task_id": task.task_id,
                        "user_id": task.user_id,
                        "status": task.status,
                        "task_type": task.task_type,
                        "payload": task.payload,
                        "result": task.result,
                        "created_at": task.created_at.isoformat(),
                        "updated_at": task.updated_at.isoformat(),
                        "metadata": task.metadata_,
                    }
                    for task in tasks
                ]
        except Exception as e:
            _log.error("task_db_list_failed", error=str(e))
            return []


# Global task store instance
task_store = TaskStore()


async def get_task_store() -> TaskStore:
    """Factory function to get the configured task store instance."""
    return task_store
