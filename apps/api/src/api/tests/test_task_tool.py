"""Tests for task_tool assistant tools."""

from __future__ import annotations

import pytest

from api.assistant_tools import task_tool  # noqa: F401 - registration side effect
from api.assistant_tools.registry import TOOL_REGISTRY
from api.storage.tasks import task_store


@pytest.fixture(autouse=True)
def isolated_task_store():
    prev_use_db = task_store.use_db
    prev_data = dict(task_store._in_memory_tasks)
    task_store.use_db = False
    task_store._in_memory_tasks = {}
    try:
        yield
    finally:
        task_store.use_db = prev_use_db
        task_store._in_memory_tasks = prev_data


class TestTaskToolRegistration:
    EXPECTED = {"create_task", "list_tasks", "update_task", "complete_task"}

    def test_tools_registered(self):
        assert self.EXPECTED.issubset(TOOL_REGISTRY.keys())

    def test_tools_category(self):
        for name in self.EXPECTED:
            assert TOOL_REGISTRY[name].category == "tasks"


class TestTaskLifecycle:
    @pytest.mark.asyncio
    async def test_create_and_list_tasks(self):
        created = await TOOL_REGISTRY["create_task"].handler(
            title="Ship release notes",
            details="Write concise changelog",
            priority="high",
            tags=["release"],
            user_id="u1",
        )
        assert created["created"] is True
        task_id = created["task"]["task_id"]

        listed = await TOOL_REGISTRY["list_tasks"].handler(status="pending", limit=10, user_id="u1")
        assert listed["count"] == 1
        assert listed["tasks"][0]["task_id"] == task_id
        assert listed["tasks"][0]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_update_task_partial_and_status(self):
        created = await TOOL_REGISTRY["create_task"].handler(title="Draft spec", user_id="u1")
        task_id = created["task"]["task_id"]

        updated = await TOOL_REGISTRY["update_task"].handler(
            task_id=task_id,
            status="in_progress",
            details="First draft complete",
            user_id="u1",
        )
        assert updated["updated"] is True
        assert updated["task"]["status"] == "in_progress"
        assert updated["task"]["details"] == "First draft complete"

    @pytest.mark.asyncio
    async def test_complete_task(self):
        created = await TOOL_REGISTRY["create_task"].handler(title="Close loop", user_id="u1")
        task_id = created["task"]["task_id"]

        completed = await TOOL_REGISTRY["complete_task"].handler(
            task_id=task_id,
            completion_note="Done",
            user_id="u1",
        )
        assert completed["completed"] is True
        assert completed["task"]["status"] == "completed"
        assert completed["task"]["completion_note"] == "Done"

    @pytest.mark.asyncio
    async def test_invalid_status_rejected(self):
        created = await TOOL_REGISTRY["create_task"].handler(title="X", user_id="u1")
        task_id = created["task"]["task_id"]

        bad = await TOOL_REGISTRY["update_task"].handler(
            task_id=task_id, status="archived", user_id="u1"
        )
        assert "error" in bad
        assert "Invalid status" in bad["error"]

    @pytest.mark.asyncio
    async def test_unknown_task_id_errors(self):
        missing = await TOOL_REGISTRY["update_task"].handler(task_id="does-not-exist", title="noop")
        assert "error" in missing
        assert "Task not found" in missing["error"]
