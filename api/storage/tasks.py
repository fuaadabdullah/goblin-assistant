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

    # Database implementation methods (placeholders for now)
    async def _get_task_from_db(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve task from database."""
        # TODO: Implement with SQLAlchemy or similar
        # Example:
        # async with self._get_db_session() as session:
        #     result = await session.execute(
        #         select(Task).where(Task.id == task_id)
        #     )
        #     task = result.scalar_one_or_none()
        #     return task.to_dict() if task else None
        return None

    async def _save_task_to_db(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """Save task to database."""
        # TODO: Implement with SQLAlchemy or similar
        # Example:
        # async with self._get_db_session() as session:
        #     task = Task(id=task_id, **task_data)
        #     await session.merge(task)  # Insert or update
        #     await session.commit()
        pass

    async def _delete_task_from_db(self, task_id: str) -> bool:
        """Delete task from database."""
        # TODO: Implement with SQLAlchemy or similar
        # Example:
        # async with self._get_db_session() as session:
        #     result = await session.execute(
        #         delete(Task).where(Task.id == task_id)
        #     )
        #     await session.commit()
        #     return result.rowcount > 0
        return False

    async def _list_tasks_from_db(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List tasks from database."""
        # TODO: Implement with SQLAlchemy or similar
        # Example:
        # async with self._get_db_session() as session:
        #     query = select(Task).order_by(Task.created_at.desc()).limit(limit)
        #     if status:
        #         query = query.where(Task.status == status)
        #     result = await session.execute(query)
        #     tasks = result.scalars().all()
        #     return [task.to_dict() for task in tasks]
        return []

    @contextmanager
    def _get_db_session(self):
        """Context manager for database sessions."""
        # TODO: Implement with SQLAlchemy or similar
        # This would yield a database session
        # For now, just yield None as placeholder
        yield None


# Global task store instance
task_store = TaskStore()


async def get_task_store() -> TaskStore:
    """Factory function to get the configured task store instance."""
    return task_store
