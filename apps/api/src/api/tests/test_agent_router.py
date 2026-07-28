from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth.router import get_current_user
from api.routes.agent import router
from api.storage.tasks import task_store


@pytest.fixture(autouse=True)
def _clear_task_store():
    task_store._in_memory_tasks = {}
    yield
    task_store._in_memory_tasks = {}


def _client() -> TestClient:
    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-123")
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def test_submit_agent_task_persists_and_returns_queued_record():
    client = _client()

    with (
        patch("api.routes.agent._dispatch_to_worker", new_callable=AsyncMock),
        patch("api.routes.agent.asyncio.create_task", return_value=None),
    ):
        response = client.post(
            "/api/v1/agent/task",
            json={
                "task": "add rate limiting to the chat route",
                "repo_url": "https://github.com/acme/goblin-assistant",
                "tests_command": "pytest -q",
            },
        )

    assert response.status_code == 200
    body = response.json()
    task = body["data"]["task"]
    assert task["status"] == "queued"
    assert task["source"] == "ui"
    assert task["repo_url"] == "https://github.com/acme/goblin-assistant"
    assert task["tests_command"] == "pytest -q"
    assert task["workspace_id"] == "workspace-github-com-acme-goblin-assistant-main"
    assert task["sprite_name"] == "sprite-github-com-acme-goblin-assistant-main"
    assert task["architect_model"] == "router-reason"
    assert task["editor_model"] == "router-code"
    assert task["auto_commit_each_change"] is True
    assert task["repair_attempts"] == 2
    assert len(task["phase0_ci_commands"]) == 3
    assert task["worker_profile"]["github_publish"]["method"] == "repo.create_pull"
    assert task["worker_profile"]["auto_merge"] is False
    assert task["events"][0]["type"] == "task.created"

    fetched = client.get(f"/api/v1/agent/task/{task['task_id']}")
    assert fetched.status_code == 200
    fetched_task = fetched.json()["data"]
    assert fetched_task["task_id"] == task["task_id"]
    assert fetched_task["task"] == "add rate limiting to the chat route"


def test_github_webhook_normalizes_issue_payload_and_ignores_unrelated_actions():
    client = _client()

    with (
        patch("api.routes.agent._dispatch_to_worker", new_callable=AsyncMock),
        patch("api.routes.agent.asyncio.create_task", return_value=None),
    ):
        response = client.post(
            "/api/v1/agent/task/github-webhook",
            json={
                "action": "opened",
                "issue": {
                    "number": 42,
                    "title": "Add rate limiting",
                    "body": "Throttle the chat route.",
                    "html_url": "https://github.com/acme/goblin-assistant/issues/42",
                },
                "repository": {
                    "html_url": "https://github.com/acme/goblin-assistant",
                    "default_branch": "main",
                    "full_name": "acme/goblin-assistant",
                },
            },
        )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["accepted"] is True
    assert body["task"]["source"] == "github_issue"
    assert body["task"]["issue_number"] == 42
    assert body["task"]["repo_url"] == "https://github.com/acme/goblin-assistant"
    assert body["task"]["workspace_id"] == "workspace-github-com-acme-goblin-assistant-main"
    assert body["task"]["architect_model"] == "router-reason"
    assert body["task"]["repair_attempts"] == 2

    ignored = client.post(
        "/api/v1/agent/task/github-webhook",
        json={"action": "closed", "issue": {"title": "Ignore me"}},
    )
    assert ignored.status_code == 200
    ignored_body = ignored.json()["data"]
    assert ignored_body["ignored"] is True
    assert ignored_body["accepted"] is False


def test_agent_event_callback_updates_status_and_enforces_secret(monkeypatch):
    monkeypatch.setenv("AGENT_WORKER_CALLBACK_SECRET", "shared-secret")
    client = _client()

    with (
        patch("api.routes.agent._dispatch_to_worker", new_callable=AsyncMock),
        patch("api.routes.agent.asyncio.create_task", return_value=None),
    ):
        created = client.post(
            "/api/v1/agent/task",
            json={"task": "write tests", "repo_url": "https://github.com/acme/goblin-assistant"},
        )
    task_id = created.json()["data"]["task"]["task_id"]

    unauthorized = client.post(
        f"/api/v1/agent/task/{task_id}/events",
        json={
            "type": "worker.progress",
            "message": "Starting planning",
            "status": "planning",
            "phase": "planning",
        },
    )
    assert unauthorized.status_code == 403

    response = client.post(
        f"/api/v1/agent/task/{task_id}/events",
        headers={"X-Agent-Worker-Token": "shared-secret"},
        json={
            "type": "worker.progress",
            "message": "PR opened",
            "status": "pr_opened",
            "phase": "publishing",
            "result": {"pr_url": "https://github.com/acme/goblin-assistant/pull/123"},
        },
    )

    assert response.status_code == 200
    task = response.json()["data"]
    assert task["status"] == "pr_opened"
    assert task["phase"] == "publishing"
    assert task["pr_url"] == "https://github.com/acme/goblin-assistant/pull/123"
    assert task["events"][-1]["type"] == "worker.progress"
