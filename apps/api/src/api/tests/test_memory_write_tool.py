from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from api.assistant_tools.skills.memory_write import _handle_memory_write


@pytest.mark.asyncio
async def test_memory_write_forwards_goal_category_to_memory_core():
    with patch(
        "api.assistant_tools.skills.memory_write.memory_core_service.ingest_memory_fact",
        new=AsyncMock(return_value={"id": "mem-1"}),
    ) as ingest:
        result = await _handle_memory_write(
            fact="Launch beta in Q3.",
            category="goal",
            user_id="user-1",
            conversation_id="conv-1",
        )

    assert result["status"] == "stored"
    assert result["category"] == "goal"
    assert result["storage_category"] == "goal"
    ingest.assert_awaited_once()
    kwargs = ingest.await_args.kwargs
    assert kwargs["fact_text"] == "Launch beta in Q3."
    assert kwargs["category"] == "goal"
    assert kwargs["explicit_kind"] == "goal"
    assert kwargs["metadata"]["requested_category"] == "goal"
    assert kwargs["metadata"]["storage_category"] == "goal"


@pytest.mark.asyncio
async def test_memory_write_maps_project_alias_to_project_state():
    with patch(
        "api.assistant_tools.skills.memory_write.memory_core_service.ingest_memory_fact",
        new=AsyncMock(return_value={"id": "mem-2"}),
    ) as ingest:
        result = await _handle_memory_write(
            fact="GoblinOS routing should stay deterministic.",
            category="project",
            user_id="user-1",
            conversation_id="conv-2",
        )

    assert result["status"] == "stored"
    assert result["category"] == "project"
    assert result["storage_category"] == "project_state"
    ingest.assert_awaited_once()
    kwargs = ingest.await_args.kwargs
    assert kwargs["category"] == "project_state"
    assert kwargs["explicit_kind"] == "project_state"
    assert kwargs["metadata"]["requested_category"] == "project"
    assert kwargs["metadata"]["storage_category"] == "project_state"
