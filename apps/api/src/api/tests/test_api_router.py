"""Tests for api.api_router."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import api_router


@pytest.fixture(autouse=True)
def _clear_streams():
    from api.services import stream_state_store

    stream_state_store._stream_store_singleton = None
    yield
    stream_state_store._stream_store_singleton = None


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(api_router.router)
    return TestClient(app)


def test_simple_chat_returns_provider_result_text():
    client = _client()

    with patch(
        "api.api_router.invoke_provider",
        new_callable=AsyncMock,
        return_value={
            "ok": True,
            "result": {"text": "hello back"},
            "provider": "openai",
            "model": "gpt-4o-mini",
        },
    ):
        response = client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["result"] == {"text": "hello back"}
    assert data["provider"] == "openai"
    assert data["model"] == "gpt-4o-mini"


def test_simple_chat_returns_error_payload_for_provider_failure_and_exception():
    client = _client()

    with patch(
        "api.api_router.invoke_provider",
        new_callable=AsyncMock,
        return_value={"ok": False, "error": "provider down"},
    ):
        failed = client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )

    with patch(
        "api.api_router.invoke_provider",
        new_callable=AsyncMock,
        side_effect=RuntimeError("boom"),
    ):
        errored = client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )

    assert failed.status_code == 200
    assert failed.json()["ok"] is False
    assert failed.json()["error"] == "provider down"
    assert errored.status_code == 200
    assert errored.json()["ok"] is False
    assert "boom" in errored.json()["error"]


def test_simple_chat_rejects_oversized_message():
    client = _client()
    max_len = api_router.InputSanitizer.MAX_MESSAGE_LENGTH

    response = client.post(
        "/api/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "x" * (max_len + 1),
                }
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert "maximum length" in data["error"]


def test_generate_requires_messages_or_prompt():
    client = _client()

    response = client.post("/api/generate", json={"model": "gpt-4o-mini"})

    assert response.status_code == 400
    assert response.json()["detail"] == ("Either 'messages' or 'prompt' must be provided")


def test_generate_uses_prompt_and_returns_openai_style_response():
    client = _client()

    with patch(
        "api.api_router.invoke_provider",
        new_callable=AsyncMock,
        return_value={"ok": True, "text": "prompt reply"},
    ):
        response = client.post(
            "/api/generate",
            json={"prompt": "Tell me a joke", "provider": "mock"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "prompt reply"
    assert data["choices"][0]["message"]["content"] == "prompt reply"


def test_generate_handles_oversized_prompt_provider_error_and_exception():
    client = _client()
    max_len = api_router.InputSanitizer.MAX_MESSAGE_LENGTH

    oversized = client.post("/api/generate", json={"prompt": "x" * (max_len + 1)})
    assert oversized.status_code == 413

    with patch(
        "api.api_router.invoke_provider",
        new_callable=AsyncMock,
        return_value={"ok": False, "error": "nope"},
    ):
        provider_error = client.post("/api/generate", json={"prompt": "hi"})

    with patch(
        "api.api_router.invoke_provider",
        new_callable=AsyncMock,
        side_effect=RuntimeError("explode"),
    ):
        exception_response = client.post("/api/generate", json={"prompt": "hi"})

    assert provider_error.status_code == 200
    assert provider_error.json()["error"] == "nope"
    assert exception_response.status_code == 200
    assert exception_response.json()["error"] == "explode"


def test_route_task_returns_task_identifier():
    client = _client()

    with patch(
        "api.api_router.route_task_runtime",
        new_callable=AsyncMock,
        return_value={"ok": True, "result": {"text": "hi"}, "selected_provider": "openai"},
    ):
        response = client.post(
            "/api/route_task",
            json={"task_type": "chat", "payload": {"message": "hi"}},
        )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["message"] == "Task routed successfully"
    assert response.json()["task_id"]


def test_route_task_failure_and_exception_paths():
    client = _client()
    fake_store = MagicMock()
    fake_store.save_task = AsyncMock()
    fake_store.update_task_status = AsyncMock()

    with (
        patch("api.api_router.get_task_store", new_callable=AsyncMock, return_value=fake_store),
        patch(
            "api.api_router.route_task_runtime",
            new_callable=AsyncMock,
            return_value={"ok": False, "error": "routing failed", "providers_tried": ["openai"]},
        ),
    ):
        failed = client.post(
            "/api/route_task",
            json={"task_type": "chat", "payload": {"message": "hi"}},
        )

    assert failed.status_code == 200
    assert failed.json()["ok"] is False
    assert failed.json()["providers_tried"] == ["openai"]

    with (
        patch("api.api_router.get_task_store", new_callable=AsyncMock, return_value=fake_store),
        patch(
            "api.api_router.route_task_runtime",
            new_callable=AsyncMock,
            side_effect=RuntimeError("kaboom"),
        ),
    ):
        errored = client.post(
            "/api/route_task",
            json={"task_type": "chat", "payload": {"message": "hi"}},
        )

    assert errored.status_code == 500
    assert "Routing failed: kaboom" in errored.json()["detail"]


def test_start_poll_and_cancel_stream_task_flow():
    client = _client()
    store_data: dict[str, dict] = {}

    class _FakeStore:
        async def create_stream(self, stream_id: str, metadata):
            store_data[stream_id] = {"status": "running", "chunks": [], "metadata": metadata}

        async def poll_stream(self, stream_id: str):
            stream = store_data.get(stream_id)
            if stream is None:
                return None
            chunks = list(stream["chunks"])
            stream["chunks"] = []
            return {
                "stream_id": stream_id,
                "status": stream["status"],
                "chunks": chunks,
                "done": stream["status"] == "completed",
            }

        async def cancel_stream(self, stream_id: str):
            stream = store_data.get(stream_id)
            if stream is None:
                return False
            stream["status"] = "cancelled"
            return True

    with (
        patch(
            "api.api_router.asyncio.create_task",
            new=MagicMock(),
        ) as mock_task,
        patch("api.api_router.get_stream_state_store", return_value=_FakeStore()),
    ):
        start = client.post(
            "/api/route_task_stream_start",
            json={"goblin": "docs-writer", "task": "Write docs"},
        )
        assert start.status_code == 200
        stream_id = start.json()["stream_id"]
        mock_task.assert_called_once()

        poll = client.get(f"/api/route_task_stream_poll/{stream_id}")
        assert poll.status_code == 200
        assert poll.json()["status"] == "running"
        assert poll.json()["chunks"] == []
        assert poll.json()["done"] is False

        cancel = client.post(f"/api/route_task_stream_cancel/{stream_id}")
        assert cancel.status_code == 200
        assert cancel.json()["status"] == "cancelled"


def test_start_stream_task_failure_and_cancel_404():
    client = _client()

    with patch(
        "api.api_router.get_stream_state_store",
        side_effect=RuntimeError("store unavailable"),
    ):
        failed = client.post(
            "/api/route_task_stream_start",
            json={"goblin": "docs-writer", "task": "Write docs"},
        )

    assert failed.status_code == 500
    assert "Failed to start stream task: store unavailable" in failed.json()["detail"]

    class _MissingStore:
        async def cancel_stream(self, stream_id: str):
            del stream_id
            return False

    with patch("api.api_router.get_stream_state_store", return_value=_MissingStore()):
        missing = client.post("/api/route_task_stream_cancel/missing")

    assert missing.status_code == 404


def test_poll_stream_task_404_for_missing_stream():
    client = _client()

    response = client.get("/api/route_task_stream_poll/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Stream not found"


def test_get_goblins_and_history_limits():
    client = _client()
    fake_store = MagicMock()
    fake_store.list_tasks = AsyncMock(
        return_value=[
            {
                "task_id": "t1",
                "task_type": "chat",
                "payload": {"task": "Write docs"},
                "status": "completed",
                "result": {"selected_provider": "docs-writer", "result": {"text": "done"}},
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:00:10",
            }
        ]
    )

    with (
        patch(
            "api.api_router.dispatcher.get_provider_inventory",
            new_callable=AsyncMock,
            return_value=[
                {
                    "id": "docs-writer",
                    "name": "Docs Writer",
                    "configured": True,
                    "healthy": True,
                    "tier": "cloud",
                }
            ],
        ),
        patch("api.api_router.get_task_store", new_callable=AsyncMock, return_value=fake_store),
        patch(
            "api.api_router.conversation_store.list_conversations",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        goblins = client.get("/api/goblins")
        history = client.get("/api/history/docs-writer?limit=25")

    assert goblins.status_code == 200
    assert goblins.json()[0]["id"] == "docs-writer"
    assert goblins.json()[0]["status"] == "available"

    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["goblin"] == "docs-writer"


def test_get_goblin_stats_and_empty_history_defaults():
    client = _client()
    fake_store = MagicMock()
    fake_store.list_tasks = AsyncMock(return_value=[])

    with (
        patch("api.api_router.get_task_store", new_callable=AsyncMock, return_value=fake_store),
        patch(
            "api.api_router.conversation_store.list_conversations",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "api.api_router.routing_registry.snapshot",
            return_value={
                "docs-writer": {
                    "success_rate": 0.75,
                    "total_cost_usd": 1.25,
                    "ewma_latency_ms": 321.0,
                    "last_used": 123.0,
                }
            },
        ),
    ):
        stats = client.get("/api/stats/docs-writer")
        history = client.get("/api/history/docs-writer?limit=999")

    assert stats.status_code == 200
    assert stats.json()["goblin_id"] == "docs-writer"
    assert stats.json()["total_tasks"] == 75
    assert history.status_code == 200
    assert history.json() == []


def test_get_goblins_degrades_when_health_flag_is_missing():
    client = _client()

    with patch(
        "api.api_router.dispatcher.get_provider_inventory",
        new_callable=AsyncMock,
        return_value=[
            {
                "id": "docs-writer",
                "name": "Docs Writer",
                "configured": True,
                "tier": "cloud",
            }
        ],
    ):
        response = client.get("/api/goblins")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == "docs-writer"
    assert body[0]["status"] == "degraded"


def test_get_goblin_history_includes_chat_completions_from_conversations():
    client = _client()
    fake_store = MagicMock()
    fake_store.list_tasks = AsyncMock(return_value=[])

    fake_conversation = MagicMock(
        conversation_id="conv-1",
        messages=[
            MagicMock(
                role="user",
                content="Draft release notes",
                message_id="u1",
                timestamp="2026-01-01T00:00:00",
                metadata={},
            ),
            MagicMock(
                role="assistant",
                content="Release notes drafted.",
                message_id="a1",
                timestamp="2026-01-01T00:00:02",
                metadata={"provider": "docs-writer", "model": "gpt-4o-mini"},
            ),
        ],
    )

    with (
        patch("api.api_router.get_task_store", new_callable=AsyncMock, return_value=fake_store),
        patch(
            "api.api_router.conversation_store.list_conversations",
            new_callable=AsyncMock,
            return_value=[fake_conversation],
        ),
    ):
        history = client.get("/api/history/docs-writer?limit=10")

    assert history.status_code == 200
    body = history.json()
    assert len(body) == 1
    assert body[0]["task"] == "Draft release notes"
    assert body[0]["response"] == "Release notes drafted."
    assert body[0]["goblin"] == "docs-writer"


def test_orchestration_parse_stores_plan_and_execute_runs_background_task():
    client = _client()

    _fake_steps = [
        {
            "id": "general-goblin",
            "goblin": "general-goblin",
            "task": "write docs",
            "dependencies": [],
        }
    ]
    _plan_task = {
        "task_id": "plan-1",
        "task_type": "orchestration.plan",
        "status": "pending",
        "payload": {"text": "write docs", "default_goblin": "docs-writer"},
        "result": {"steps": _fake_steps, "complexity": "low", "estimated_duration": 30},
    }
    _execution_task = {
        "task_id": "exec-1",
        "task_type": "orchestration.execute",
        "status": "completed",
        "payload": {"plan_id": "plan-1"},
        "result": {
            "steps": [
                {
                    **_fake_steps[0],
                    "status": "completed",
                    "result": "done",
                    "provider_used": "openai",
                    "cost_usd": 0.001,
                    "duration_ms": 800,
                    "error": None,
                }
            ],
            "total_cost": 0.001,
            "total_duration_ms": 800,
        },
        "created_at": 0.0,
    }

    fake_store = MagicMock()
    fake_store.save_task = AsyncMock()
    fake_store.get_task = AsyncMock(return_value=_plan_task)
    fake_store.list_tasks = AsyncMock(return_value=[_execution_task])
    fake_store.update_task_status = AsyncMock()

    from api.core.orchestration import OrchestrationPlan, OrchestrationStep

    fake_plan = OrchestrationPlan(
        steps=[OrchestrationStep(goblin="general-goblin", task="write docs")],
        complexity="low",
        estimated_duration=30,
    )

    with (
        patch("api.orchestration_router.parse_natural_language", return_value=fake_plan),
        patch(
            "api.orchestration_router.get_task_store",
            new_callable=AsyncMock,
            return_value=fake_store,
        ),
        patch("api.orchestration_router.asyncio.create_task", new=MagicMock()),
    ):
        parsed = client.post(
            "/api/orchestrate/parse",
            json={"text": "write docs", "default_goblin": "docs-writer"},
        )
        assert parsed.status_code == 200
        parse_data = parsed.json()
        assert "plan_id" in parse_data
        assert parse_data["steps"][0]["goblin"] == "general-goblin"
        assert parse_data["complexity"] == "low"

        executed = client.post("/api/orchestrate/execute", params={"plan_id": "plan-1"})
        assert executed.status_code == 200
        exec_data = executed.json()
        assert exec_data["plan_id"] == "plan-1"
        assert exec_data["status"] == "started"
        assert "execution_id" in exec_data

        poll = client.get("/api/orchestrate/plans/plan-1")
        assert poll.status_code == 200
        poll_data = poll.json()
        assert poll_data["plan_id"] == "plan-1"
        assert poll_data["status"] == "completed"
        assert len(poll_data["steps"]) == 1
        assert poll_data["steps"][0]["status"] == "completed"
        assert poll_data["total_cost"] == 0.001


def test_orchestration_execute_and_plan_not_found_paths():
    client = _client()
    fake_store = MagicMock()
    fake_store.get_task = AsyncMock(return_value=None)
    fake_store.list_tasks = AsyncMock(return_value=[])

    with patch("api.api_router.get_task_store", new_callable=AsyncMock, return_value=fake_store):
        missing_exec = client.post("/api/orchestrate/execute", params={"plan_id": "missing"})
        missing_plan = client.get("/api/orchestrate/plans/missing")

    assert missing_exec.status_code == 404
    assert missing_plan.status_code == 404
