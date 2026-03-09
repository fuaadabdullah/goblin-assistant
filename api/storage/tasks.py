"""
Persistent storage wrapper for tasks with database and in-memory backends.
"""

from contextlib import contextmanager
from typing import Dict, Any, Optional, List
import os
from datetime import datetime


class TaskStore:
    """Storage abstraction for task data with database and in-memory backends."""

    def __init__(self):
        self.use_db = os.getenv("USE_DATABASE", "false").lower() == "true"
        self._in_memory_tasks: Dict[str, Dict[str, Any]] = {}

        # Initialize database connection if needed
        if self.use_db:
            self._init_db()

    def _init_db(self):
        """Initialize database connection and tables."""
        # TODO: Implement actual database initialization
        # This would typically use SQLAlchemy, asyncpg, or similar
        # For now, we'll keep it as a placeholder
        pass

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a task by ID."""
        if self.use_db:
            return await self._get_task_from_db(task_id)
        else:
            return self._in_memory_tasks.get(task_id)

    async def save_task(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """Save or update a task."""
        # Add timestamps
        now = datetime.utcnow().isoformat()
        if "created_at" not in task_data:
            task_data["created_at"] = now
        task_data["updated_at"] = now

        if self.use_db:
            await self._save_task_to_db(task_id, task_data)
        else:
            self._in_memory_tasks[task_id] = task_data

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID. Returns True if task was found and deleted."""
        if self.use_db:
            return await self._delete_task_from_db(task_id)
        else:
            return self._in_memory_tasks.pop(task_id, None) is not None

    async def list_tasks(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List tasks, optionally filtered by status."""
        if self.use_db:
            return await self._list_tasks_from_db(status, limit)
        else:
            tasks = list(self._in_memory_tasks.values())
            if status:
                tasks = [t for t in tasks if t.get("status") == status]
            return tasks[-limit:]  # Return most recent tasks

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

    # Database implementation methods
    async def _get_task_from_db(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve task from database."""
        try:
            from .models import TaskModel
            from .database import get_db_context
            from sqlalchemy import select

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
            print(f"Error retrieving task from database: {e}")
            return None

    async def _save_task_to_db(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """Save task to database."""
        try:
            from .models import TaskModel
            from .database import get_db_context
            from sqlalchemy import select

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
                        created_at=datetime.fromisoformat(task_data["created_at"]) if "created_at" in task_data else datetime.utcnow(),
                        updated_at=datetime.fromisoformat(task_data["updated_at"]) if "updated_at" in task_data else datetime.utcnow(),
                        metadata_=task_data.get("metadata", {}),
                    )
                    session.add(task)
        except Exception as e:
            print(f"Error saving task to database: {e}")

    async def _delete_task_from_db(self, task_id: str) -> bool:
        """Delete task from database."""
        try:
            from .models import TaskModel
            from .database import get_db_context
            from sqlalchemy import delete

            async with get_db_context() as session:
                result = await session.execute(
                    delete(TaskModel).where(TaskModel.task_id == task_id)
                )
                return result.rowcount > 0
        except Exception as e:
            print(f"Error deleting task from database: {e}")
            return False

    async def _list_tasks_from_db(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List tasks from database."""
        try:
            from .models import TaskModel
            from .database import get_db_context
            from sqlalchemy import select, desc

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
            print(f"Error listing tasks from database: {e}")
            return []

    @contextmanager
    def _get_db_session(self):
        """Context manager for database sessions (deprecated - use get_db_context instead)."""
        # This method is deprecated in favor of using get_db_context() directly
        # Kept for backward compatibility
        yield None


# Global task store instance
task_store = TaskStore()


async def get_task_store() -> TaskStore:
    """Factory function to get the configured task store instance."""
    return task_store
