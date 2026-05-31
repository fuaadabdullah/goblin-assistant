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
    ):
        goblins = client.get("/api/goblins")
        history = client.get("/api/history/docs-writer?limit=25")

    assert goblins.status_code == 200
    assert goblins.json()[0]["id"] == "docs-writer"
    assert goblins.json()[0]["status"] == "available"

    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["goblin"] == "docs-writer"


def test_orchestration_routes_delegate_and_return_payloads():
    client = _client()

    with patch(
        "api.api_router.create_simple_orchestration_plan",
        return_value={"ok": True, "plan_id": "plan-1"},
    ):
        parsed = client.post(
            "/api/orchestrate/parse",
            json={"text": "write docs", "default_goblin": "docs-writer"},
        )

    executed = client.post("/api/orchestrate/execute", params={"plan_id": "plan-1"})
    plan = client.get("/api/orchestrate/plans/plan-1")

    assert parsed.status_code == 200
    assert parsed.json() == {"ok": True, "plan_id": "plan-1"}

    assert executed.status_code == 200
    assert executed.json()["plan_id"] == "plan-1"
    assert executed.json()["status"] == "started"

    assert plan.status_code == 200
    assert plan.json()["plan_id"] == "plan-1"
    assert plan.json()["status"] == "started"
