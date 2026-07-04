"""Self-development agent task orchestration routes.

The backend persists task state and normalizes triggers from the UI or GitHub
issues. A separate Fly.io worker runs the repo-edit/test/PR loop and reports
progress back through the task event endpoint.
"""

from __future__ import annotations

import asyncio
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from api.auth.router import get_current_user
from api.core.contracts import SuccessEnvelope
from api.observability.telemetry import record_agent_task_event
from api.services.agent_workflow import (
    ARCHITECT_MODEL,
    EDITOR_MODEL,
    build_agent_worker_payload,
    build_worker_profile,
    derive_workspace_contract,
    extract_contract_fields,
    resolve_default_repair_attempts,
)
from api.storage.tasks import get_task_store

router = APIRouter(prefix="/agent", tags=["agent"])

_TASK_TYPE = "agent_task"
_DEFAULT_TEST_COMMAND = "make test-critical"
_DEFAULT_BASE_BRANCH = "main"
_EVENT_STATES = {
    "queued",
    "accepted",
    "planning",
    "editing",
    "testing",
    "repairing",
    "publishing",
    "pr_opened",
    "failed",
    "cancelled",
}


def _utcnow() -> str:
    return datetime.utcnow().isoformat()


def _detail_message(prefix: str, error: Exception) -> str:
    message = str(error).strip()
    if message:
        return f"{prefix}: {message}"
    return f"{prefix}: Request failed"


def _slugify(value: str, fallback: str = "task") -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def _resolve_repo_url(explicit_repo_url: Optional[str]) -> str:
    if explicit_repo_url and explicit_repo_url.strip():
        return explicit_repo_url.strip()

    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    server_url = os.getenv("GITHUB_SERVER_URL", "https://github.com").strip()
    if repository:
        return f"{server_url.rstrip('/')}/{repository}"

    fallback = os.getenv("AGENT_REPOSITORY_URL", "").strip()
    if fallback:
        return fallback

    raise HTTPException(
        status_code=400,
        detail="repo_url is required or AGENT_REPOSITORY_URL/GITHUB_REPOSITORY must be set",
    )


def _resolve_worker_url() -> str:
    return os.getenv("AGENT_SPRITE_WORKER_URL", "").strip()


def _resolve_worker_secret() -> str:
    return os.getenv("AGENT_WORKER_SECRET", "").strip()


def _resolve_callback_secret() -> str:
    return os.getenv("AGENT_WORKER_CALLBACK_SECRET", "").strip()


def _resolve_backend_url() -> str:
    return os.getenv("AGENT_BACKEND_URL", "").strip() or "http://127.0.0.1:8001"


def _resolve_default_branch() -> str:
    return (
        os.getenv("AGENT_DEFAULT_BASE_BRANCH", _DEFAULT_BASE_BRANCH).strip() or _DEFAULT_BASE_BRANCH
    )


def _resolve_default_tests_command() -> str:
    return os.getenv("AGENT_TEST_COMMAND", _DEFAULT_TEST_COMMAND).strip() or _DEFAULT_TEST_COMMAND


def _resolve_request_timeout() -> float:
    raw = os.getenv("AGENT_WORKER_TIMEOUT_SECONDS", "30").strip()
    try:
        return max(5.0, float(raw))
    except ValueError:
        return 30.0


def _callback_url(task_id: str) -> str:
    return f"{_resolve_backend_url().rstrip('/')}/api/v1/agent/task/{task_id}/events"


def _event_payload(
    event_type: str,
    message: str,
    *,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "event_id": str(uuid.uuid4()),
        "type": event_type,
        "message": message,
        "timestamp": _utcnow(),
        "metadata": metadata or {},
    }


def _task_event_list(task: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = task.get("result")
    if isinstance(result, dict):
        events = result.get("events", [])
        if isinstance(events, list):
            return [event for event in events if isinstance(event, dict)]
    return []


def _task_result(task: Dict[str, Any]) -> Dict[str, Any]:
    result = task.get("result")
    return result if isinstance(result, dict) else {}


def _normalize_issue_payload(body: Dict[str, Any]) -> Dict[str, Any]:
    issue = body.get("issue") if isinstance(body.get("issue"), dict) else {}
    repository = body.get("repository") if isinstance(body.get("repository"), dict) else {}

    title = str(issue.get("title") or body.get("title") or body.get("task") or "").strip()
    description = str(
        issue.get("body") or body.get("body") or body.get("description") or ""
    ).strip()
    if not title and not description:
        raise HTTPException(
            status_code=400, detail="GitHub webhook payload is missing issue content"
        )

    repo_url = str(
        repository.get("html_url") or repository.get("clone_url") or body.get("repo_url") or ""
    ).strip()

    return {
        "task": title or description,
        "repo_url": repo_url or None,
        "base_branch": str(
            repository.get("default_branch") or body.get("base_branch") or ""
        ).strip()
        or None,
        "issue_url": str(issue.get("html_url") or body.get("issue_url") or "").strip() or None,
        "issue_number": issue.get("number")
        if isinstance(issue.get("number"), int)
        else body.get("issue_number"),
        "issue_title": title or None,
        "issue_body": description or None,
        "metadata": {
            "github_action": body.get("action"),
            "sender": (body.get("sender") or {}).get("login")
            if isinstance(body.get("sender"), dict)
            else None,
            "repository": repository.get("full_name") if isinstance(repository, dict) else None,
        },
        "source": "github_issue",
    }


class AgentTaskSubmitRequest(BaseModel):
    task: str = Field(min_length=1, max_length=10_000)
    repo_url: Optional[str] = None
    base_branch: Optional[str] = None
    branch_name: Optional[str] = None
    tests_command: Optional[str] = None
    source: str = "ui"
    issue_url: Optional[str] = None
    issue_number: Optional[int] = None
    issue_title: Optional[str] = None
    issue_body: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentTaskEventInput(BaseModel):
    type: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=10_000)
    status: Optional[str] = None
    phase: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)


class AgentTaskEvent(BaseModel):
    event_id: str
    type: str
    message: str
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentTaskRecord(BaseModel):
    task_id: str
    status: str
    phase: str
    source: str
    task: str
    repo_url: str
    base_branch: str
    branch_name: str
    tests_command: str
    issue_url: Optional[str] = None
    issue_number: Optional[int] = None
    issue_title: Optional[str] = None
    issue_body: Optional[str] = None
    worker_status: Optional[str] = None
    worker_error: Optional[str] = None
    pr_url: Optional[str] = None
    callback_url: Optional[str] = None
    workspace_id: Optional[str] = None
    workspace_family: Optional[str] = None
    sprite_name: Optional[str] = None
    checkout_ref: Optional[str] = None
    workspace_provider: Optional[str] = None
    architect_model: Optional[str] = None
    editor_model: Optional[str] = None
    aider_mode: Optional[str] = None
    auto_commit_each_change: Optional[bool] = None
    repair_attempts: Optional[int] = None
    phase0_ci_commands: List[Dict[str, Any]] = Field(default_factory=list)
    workspace: Dict[str, Any] = Field(default_factory=dict)
    worker_profile: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    events: List[AgentTaskEvent] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)


class AgentTaskEventsResponse(BaseModel):
    task_id: str
    status: str
    phase: str
    events: List[AgentTaskEvent] = Field(default_factory=list)
    total: int = 0


class AgentTaskSubmitResponse(BaseModel):
    task: AgentTaskRecord


class GitHubWebhookResponse(BaseModel):
    accepted: bool
    ignored: bool = False
    reason: Optional[str] = None
    task: Optional[AgentTaskRecord] = None


async def _persist_task(task_id: str, task_data: Dict[str, Any]) -> None:
    store = await get_task_store()
    await store.save_task(task_id, task_data)


async def _load_task(task_id: str) -> Optional[Dict[str, Any]]:
    store = await get_task_store()
    return await store.get_task(task_id)


def _record_to_model(task: Dict[str, Any]) -> AgentTaskRecord:
    payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
    result = _task_result(task)
    metadata = task.get("metadata") if isinstance(task.get("metadata"), dict) else {}
    events = [AgentTaskEvent(**event) for event in _task_event_list(task)]
    contract_fields = extract_contract_fields(task)
    return AgentTaskRecord(
        task_id=str(task.get("task_id", "")),
        status=str(task.get("status", "queued")),
        phase=str(result.get("phase") or task.get("status") or "queued"),
        source=str(payload.get("source") or metadata.get("source") or "ui"),
        task=str(payload.get("task") or ""),
        repo_url=str(payload.get("repo_url") or result.get("repo_url") or ""),
        base_branch=str(
            payload.get("base_branch") or result.get("base_branch") or _DEFAULT_BASE_BRANCH
        ),
        branch_name=str(payload.get("branch_name") or result.get("branch_name") or ""),
        tests_command=str(
            payload.get("tests_command") or result.get("tests_command") or _DEFAULT_TEST_COMMAND
        ),
        issue_url=payload.get("issue_url") or result.get("issue_url"),
        issue_number=payload.get("issue_number") or result.get("issue_number"),
        issue_title=payload.get("issue_title") or result.get("issue_title"),
        issue_body=payload.get("issue_body") or result.get("issue_body"),
        worker_status=result.get("worker_status"),
        worker_error=result.get("worker_error"),
        pr_url=result.get("pr_url"),
        callback_url=result.get("callback_url"),
        workspace_id=contract_fields["workspace_id"] or None,
        workspace_family=contract_fields["workspace_family"] or None,
        sprite_name=contract_fields["sprite_name"] or None,
        checkout_ref=contract_fields["checkout_ref"] or None,
        workspace_provider=contract_fields["workspace_provider"] or None,
        architect_model=contract_fields["architect_model"] or None,
        editor_model=contract_fields["editor_model"] or None,
        aider_mode=contract_fields["aider_mode"] or None,
        auto_commit_each_change=contract_fields["auto_commit_each_change"],
        repair_attempts=result.get("repair_attempts"),
        phase0_ci_commands=result.get("phase0_ci_commands", [])
        if isinstance(result.get("phase0_ci_commands"), list)
        else [],
        workspace=contract_fields["workspace"],
        worker_profile=contract_fields["worker_profile"],
        created_at=str(task.get("created_at", _utcnow())),
        updated_at=str(task.get("updated_at", _utcnow())),
        events=events,
        payload=payload,
        metadata=metadata,
        result=result,
    )


async def _append_event(
    task_id: str,
    *,
    event_type: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
    status: Optional[str] = None,
    phase: Optional[str] = None,
    result_updates: Optional[Dict[str, Any]] = None,
) -> AgentTaskRecord:
    task = await _load_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")

    payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
    stored_metadata = task.get("metadata") if isinstance(task.get("metadata"), dict) else {}
    result = _task_result(task)
    events = _task_event_list(task)
    events.append(_event_payload(event_type, message, metadata=metadata))
    record_agent_task_event(event=event_type, status=status or "queued")

    if result_updates:
        result.update(result_updates)
    result["events"] = events
    if phase:
        result["phase"] = phase
    if "callback_url" not in result:
        result["callback_url"] = _callback_url(task_id)

    task["payload"] = payload
    task["metadata"] = stored_metadata
    task["result"] = result
    if status:
        task["status"] = status

    await _persist_task(task_id, task)
    return _record_to_model(task)


async def _create_agent_task(request: AgentTaskSubmitRequest) -> AgentTaskRecord:
    task_id = str(uuid.uuid4())
    repo_url = _resolve_repo_url(request.repo_url)
    base_branch = request.base_branch.strip() if request.base_branch else _resolve_default_branch()
    tests_command = (
        request.tests_command.strip() if request.tests_command else _resolve_default_tests_command()
    )
    branch_name = (
        request.branch_name.strip()
        if request.branch_name
        else f"agent/{_slugify(request.task, task_id[:8])}-{task_id[:8]}"
    )
    callback_url = _callback_url(task_id)
    workspace = derive_workspace_contract(
        repo_url=repo_url,
        base_branch=base_branch,
        task_id=task_id,
        branch_name=branch_name,
    )
    worker_profile = build_worker_profile(
        tests_command=tests_command,
        base_branch=base_branch,
        branch_name=branch_name,
        repair_attempts=resolve_default_repair_attempts(),
    )

    task_data = {
        "task_id": task_id,
        "status": "queued",
        "task_type": _TASK_TYPE,
        "payload": {
            "task": request.task.strip(),
            "repo_url": repo_url,
            "base_branch": base_branch,
            "branch_name": branch_name,
            "tests_command": tests_command,
            "source": request.source.strip() or "ui",
            "issue_url": request.issue_url,
            "issue_number": request.issue_number,
            "issue_title": request.issue_title,
            "issue_body": request.issue_body,
            "metadata": request.metadata,
            "callback_url": callback_url,
            "workspace": workspace,
            "worker_profile": worker_profile,
        },
        "metadata": {
            "source": request.source.strip() or "ui",
            "repo_url": repo_url,
            "workspace_id": workspace["workspace_id"],
            "workspace_family": workspace["workspace_family"],
        },
        "result": {
            "phase": "queued",
            "worker_status": "pending",
            "callback_url": callback_url,
            "repo_url": repo_url,
            "base_branch": base_branch,
            "branch_name": branch_name,
            "tests_command": tests_command,
            "workspace_id": workspace["workspace_id"],
            "workspace_family": workspace["workspace_family"],
            "sprite_name": workspace["sprite_name"],
            "checkout_ref": workspace["checkout_ref"],
            "workspace_provider": workspace["sprite_provider"],
            "architect_model": ARCHITECT_MODEL,
            "editor_model": EDITOR_MODEL,
            "aider_mode": "architect",
            "auto_commit_each_change": True,
            "repair_attempts": worker_profile["repair_attempts"],
            "phase0_ci_commands": worker_profile["phase0_ci_commands"],
            "workspace": workspace,
            "worker_profile": worker_profile,
            "events": [
                _event_payload(
                    "task.created",
                    "Agent task queued for persistent Sprite dispatch",
                    metadata={"source": request.source.strip() or "ui"},
                )
            ],
        },
    }
    record_agent_task_event(event="task.created", status="queued")
    if request.issue_url:
        task_data["result"]["issue_url"] = request.issue_url
    if request.issue_number is not None:
        task_data["result"]["issue_number"] = request.issue_number
    if request.issue_title:
        task_data["result"]["issue_title"] = request.issue_title
    if request.issue_body:
        task_data["result"]["issue_body"] = request.issue_body

    await _persist_task(task_id, task_data)
    task = await _load_task(task_id)
    if task is None:
        raise HTTPException(status_code=500, detail="failed to persist agent task")
    return _record_to_model(task)


def _worker_payload(task: AgentTaskRecord) -> Dict[str, Any]:
    callback_secret = _resolve_callback_secret()
    return build_agent_worker_payload(
        task_id=task.task_id,
        task=task.task,
        repo_url=task.repo_url,
        base_branch=task.base_branch,
        branch_name=task.branch_name,
        tests_command=task.tests_command,
        source=task.source,
        issue={
            "url": task.issue_url,
            "number": task.issue_number,
            "title": task.issue_title,
            "body": task.issue_body,
        },
        metadata=task.metadata,
        callback_url=task.callback_url or _callback_url(task.task_id),
        callback_secret=callback_secret or None,
        workspace=task.workspace or None,
        worker_profile=task.worker_profile or None,
    )


async def _dispatch_to_worker(task_id: str) -> None:
    worker_url = _resolve_worker_url()
    if not worker_url:
        await _append_event(
            task_id,
            event_type="worker.unconfigured",
            message="AGENT_SPRITE_WORKER_URL is not set; leaving task queued",
            status="queued",
            phase="queued",
            result_updates={"worker_status": "unconfigured"},
        )
        return

    task = await _load_task(task_id)
    if task is None:
        return
    record = _record_to_model(task)

    await _append_event(
        task_id,
        event_type="worker.dispatching",
        message=f"Dispatching agent task to {worker_url}",
        status="queued",
        phase="queued",
        result_updates={"worker_status": "dispatching", "worker_url": worker_url},
    )
    record_agent_task_event(event="worker.dispatching", status="queued")

    headers = {"Content-Type": "application/json"}
    secret = _resolve_worker_secret()
    if secret:
        headers["X-Agent-Worker-Token"] = secret

    try:
        async with httpx.AsyncClient(timeout=_resolve_request_timeout()) as client:
            response = await client.post(worker_url, json=_worker_payload(record), headers=headers)
        if response.status_code not in (200, 202):
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text[:500] or "worker dispatch failed",
            )

        response_payload: Dict[str, Any]
        try:
            response_payload = response.json()
        except Exception:
            response_payload = {"raw": response.text[:1000]}

        worker_status = str(response_payload.get("status") or "accepted")
        await _append_event(
            task_id,
            event_type="worker.accepted",
            message="Worker accepted task",
            status="accepted",
            phase="accepted",
            result_updates={
                "worker_status": worker_status,
                "worker_response": response_payload,
            },
        )
    except Exception as exc:
        await _append_event(
            task_id,
            event_type="worker.dispatch_failed",
            message=_detail_message("Worker dispatch failed", exc),
            status="failed",
            phase="dispatch",
            result_updates={
                "worker_status": "failed",
                "worker_error": str(exc),
            },
        )


def _append_status_update(
    task: Dict[str, Any],
    *,
    status: Optional[str] = None,
    phase: Optional[str] = None,
    event_type: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
    result_updates: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    result = _task_result(task)
    events = _task_event_list(task)
    events.append(_event_payload(event_type, message, metadata=metadata))
    result["events"] = events
    if phase:
        result["phase"] = phase
    if result_updates:
        result.update(result_updates)
    task["result"] = result
    if status:
        task["status"] = status
    return task


@router.post("/task", response_model=SuccessEnvelope[AgentTaskSubmitResponse])
async def submit_agent_task(
    request: AgentTaskSubmitRequest,
    current_user=Depends(get_current_user),
) -> SuccessEnvelope[AgentTaskSubmitResponse]:
    """Create a new agent task and queue it for the Sprite/Aider worker."""

    if current_user is not None:
        request.metadata = {
            **request.metadata,
            "submitted_by": getattr(current_user, "id", None),
        }
    task = await _create_agent_task(request)
    asyncio.create_task(_dispatch_to_worker(task.task_id))
    return SuccessEnvelope(data=AgentTaskSubmitResponse(task=task))


@router.post("/task/github-webhook", response_model=SuccessEnvelope[GitHubWebhookResponse])
async def submit_github_issue_webhook(
    body: Dict[str, Any],
) -> SuccessEnvelope[GitHubWebhookResponse]:
    """Normalize a GitHub issue webhook into the same agent task contract."""

    action = str(body.get("action", "")).strip().lower()
    if action and action not in {"opened", "reopened", "edited", "labeled"}:
        return SuccessEnvelope(
            data=GitHubWebhookResponse(
                accepted=False,
                ignored=True,
                reason=f"ignored action '{action}'",
            )
        )

    normalized = _normalize_issue_payload(body)
    task = await _create_agent_task(
        AgentTaskSubmitRequest(
            task=normalized["task"],
            repo_url=normalized["repo_url"],
            base_branch=normalized["base_branch"],
            source=normalized["source"],
            issue_url=normalized["issue_url"],
            issue_number=normalized["issue_number"],
            issue_title=normalized["issue_title"],
            issue_body=normalized["issue_body"],
            metadata=normalized["metadata"],
        )
    )
    asyncio.create_task(_dispatch_to_worker(task.task_id))
    return SuccessEnvelope(data=GitHubWebhookResponse(accepted=True, task=task))


@router.get("/task/{task_id}", response_model=SuccessEnvelope[AgentTaskRecord])
async def get_agent_task(
    task_id: str,
    current_user=Depends(get_current_user),
) -> SuccessEnvelope[AgentTaskRecord]:
    task = await _load_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    _ = current_user
    return SuccessEnvelope(data=_record_to_model(task))


@router.get("/task/{task_id}/events", response_model=SuccessEnvelope[AgentTaskEventsResponse])
async def get_agent_task_events(
    task_id: str,
    current_user=Depends(get_current_user),
) -> SuccessEnvelope[AgentTaskEventsResponse]:
    task = await _load_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    _ = current_user
    record = _record_to_model(task)
    return SuccessEnvelope(
        data=AgentTaskEventsResponse(
            task_id=record.task_id,
            status=record.status,
            phase=record.phase,
            events=record.events,
            total=len(record.events),
        )
    )


@router.post("/task/{task_id}/events", response_model=SuccessEnvelope[AgentTaskRecord])
async def append_agent_task_event(
    task_id: str,
    request: AgentTaskEventInput,
    x_agent_worker_token: str = Header(default=""),
) -> SuccessEnvelope[AgentTaskRecord]:
    """Worker callback for progress events and final task state."""

    expected_secret = _resolve_callback_secret()
    if expected_secret and x_agent_worker_token != expected_secret:
        raise HTTPException(status_code=403, detail="unauthorized")

    task = await _load_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")

    if request.status and request.status not in _EVENT_STATES:
        raise HTTPException(status_code=400, detail="invalid task status")
    if request.phase and request.phase not in _EVENT_STATES:
        raise HTTPException(status_code=400, detail="invalid task phase")

    result_updates = dict(request.result)
    if request.phase:
        result_updates.setdefault("phase", request.phase)
    if request.status:
        result_updates.setdefault("worker_status", request.status)
        if request.status == "pr_opened":
            result_updates.setdefault("pr_url", request.result.get("pr_url"))
        if request.status == "failed":
            result_updates.setdefault(
                "worker_error", request.result.get("worker_error") or request.message
            )

    task = _append_status_update(
        task,
        status=request.status or task.get("status"),
        phase=request.phase or request.status or _task_result(task).get("phase") or "queued",
        event_type=request.type,
        message=request.message,
        metadata=request.metadata,
        result_updates=result_updates,
    )
    await _persist_task(task_id, task)
    return SuccessEnvelope(data=_record_to_model(task))
