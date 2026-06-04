from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .core.orchestration import parse_natural_language
from .input_validation import InputSanitizer
from .providers.dispatcher import dispatcher, invoke_provider
from .routing.router import registry as routing_registry
from .routing.router import route_task as route_task_runtime
from .services.orchestration_executor import execute_orchestration_plan
from .services.stream_state_store import get_stream_state_store
from .services.task_streaming import run_task_stream_to_state
from .storage import conversation_store
from .storage.tasks import get_task_store

# Backward-compatible alias preserved for tests/integrations still patching
# `api.api_router.create_simple_orchestration_plan`.
create_simple_orchestration_plan = parse_natural_language

router = APIRouter(prefix="/api", tags=["api"])


class SimpleChatMessage(BaseModel):
    role: str
    content: str


class SimpleChatRequest(BaseModel):
    messages: List[SimpleChatMessage]
    model: Optional[str] = None
    provider: Optional[str] = None
    stream: Optional[bool] = False


class SimpleChatResponse(BaseModel):
    ok: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None


class GenerateRequest(BaseModel):
    messages: Optional[List[SimpleChatMessage]] = None
    prompt: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None


class GenerateResponse(BaseModel):
    content: Optional[str] = None
    choices: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class RouteTaskRequest(BaseModel):
    task_type: str
    payload: Dict[str, Any]
    prefer_local: Optional[bool] = False
    prefer_cost: Optional[bool] = False
    max_retries: Optional[int] = 2
    stream: Optional[bool] = False


class StreamTaskRequest(BaseModel):
    goblin: str
    task: str
    code: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None


class StreamResponse(BaseModel):
    stream_id: str
    status: str = "started"


class ParseOrchestrationRequest(BaseModel):
    text: str
    default_goblin: Optional[str] = None


def _extract_result_text(response: Dict[str, Any]) -> str:
    result_data = response.get("result", {})
    if isinstance(result_data, dict):
        text = result_data.get("text")
        if isinstance(text, str) and text:
            return text
    fallback_text = response.get("text")
    if isinstance(fallback_text, str):
        return fallback_text
    return ""


def _build_stream_messages(request: StreamTaskRequest) -> List[Dict[str, str]]:
    payload_lines = [request.task.strip()]
    if request.code:
        payload_lines.append("\nCode:\n" + request.code.strip())
    user_message = "\n".join(line for line in payload_lines if line)
    return [{"role": "user", "content": user_message}]


def _timestamp_sort_key(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).timestamp()
        except ValueError:
            return 0.0
    return 0.0


async def _collect_chat_history_entries(goblin_id: str, limit: int = 500) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    conversations = await conversation_store.list_conversations(limit=limit)

    for conversation in conversations:
        last_user_prompt = ""
        for message in conversation.messages:
            if message.role == "user":
                last_user_prompt = message.content
                continue

            if message.role != "assistant":
                continue

            metadata = message.metadata if isinstance(message.metadata, dict) else {}
            provider = metadata.get("provider")
            if provider and provider != goblin_id:
                continue

            timestamp = message.timestamp
            entries.append(
                {
                    "id": message.message_id,
                    "goblin": goblin_id,
                    "task": last_user_prompt or "chat",
                    "response": message.content,
                    "timestamp": (
                        timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp
                    ),
                    "kpis": f"status:completed source:chat conversation:{conversation.conversation_id}",
                }
            )

    return entries


@router.post("/chat", response_model=SimpleChatResponse)
async def simple_chat(request: SimpleChatRequest):
    try:
        for msg in request.messages:
            if len(msg.content) > InputSanitizer.MAX_MESSAGE_LENGTH:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        "Message content exceeds maximum length of "
                        f"{InputSanitizer.MAX_MESSAGE_LENGTH} characters"
                    ),
                )

        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        provider = request.provider or "auto"
        model = request.model

        response = await invoke_provider(
            pid=provider,
            model=model,
            payload={"messages": messages, "model": model},
            timeout_ms=30000,
            stream=bool(request.stream),
        )
        if isinstance(response, dict) and response.get("ok"):
            text = _extract_result_text(response)
            result_data = response.get("result", {})
            return SimpleChatResponse(
                ok=True,
                result={"text": text} if text else result_data,
                provider=str(response.get("provider", "unknown")),
                model=str(response.get("model", "unknown")),
            )
        error_msg = (
            response.get("error", "Unknown error") if isinstance(response, dict) else str(response)
        )
        return SimpleChatResponse(ok=False, error=str(error_msg))
    except HTTPException as exc:
        return SimpleChatResponse(ok=False, error=str(exc.detail))
    except Exception as exc:
        return SimpleChatResponse(ok=False, error=str(exc))


@router.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    try:
        if not request.messages and not request.prompt:
            raise HTTPException(
                status_code=400,
                detail="Either 'messages' or 'prompt' must be provided",
            )

        if request.messages:
            for msg in request.messages:
                if len(msg.content) > InputSanitizer.MAX_MESSAGE_LENGTH:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "Message content exceeds maximum length of "
                            f"{InputSanitizer.MAX_MESSAGE_LENGTH} characters"
                        ),
                    )
            messages = [{"role": m.role, "content": m.content} for m in request.messages]
        else:
            prompt = request.prompt or ""
            if len(prompt) > InputSanitizer.MAX_MESSAGE_LENGTH:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"Prompt exceeds maximum length of "
                        f"{InputSanitizer.MAX_MESSAGE_LENGTH} characters"
                    ),
                )
            messages = [{"role": "user", "content": prompt}]

        response = await invoke_provider(
            pid=request.provider or "auto",
            model=request.model,
            payload={"messages": messages, "model": request.model},
            timeout_ms=30000,
            stream=False,
        )
        if isinstance(response, dict) and response.get("ok"):
            text = _extract_result_text(response)
            return GenerateResponse(
                content=text,
                choices=[{"message": {"role": "assistant", "content": text}}],
            )
        error_msg = (
            response.get("error", "Unknown error") if isinstance(response, dict) else str(response)
        )
        return GenerateResponse(error=str(error_msg))
    except HTTPException:
        raise
    except Exception as exc:
        return GenerateResponse(error=str(exc))


@router.post("/route_task")
async def route_task(request: RouteTaskRequest):
    try:
        task_id = str(uuid.uuid4())
        store = await get_task_store()
        await store.save_task(
            task_id,
            {
                "status": "started",
                "task_type": request.task_type,
                "payload": request.payload,
                "metadata": {"source": "legacy_api_router"},
            },
        )
        result = await route_task_runtime(
            task_type=request.task_type,
            payload=request.payload,
            prefer_local=bool(request.prefer_local),
            prefer_cost=bool(request.prefer_cost),
            max_retries=int(request.max_retries or 2),
            stream=bool(request.stream),
        )
        if isinstance(result, dict) and result.get("ok"):
            await store.update_task_status(task_id, "completed", result=result)
            return {
                "ok": True,
                "message": "Task routed successfully",
                "task_id": task_id,
                "result": result,
            }
        await store.update_task_status(
            task_id, "failed", result=result if isinstance(result, dict) else {}
        )
        return {
            "ok": False,
            "task_id": task_id,
            "error": (
                result.get("error", "Routing failed") if isinstance(result, dict) else str(result)
            ),
            "providers_tried": (
                result.get("providers_tried", []) if isinstance(result, dict) else []
            ),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Routing failed: {exc}") from exc


@router.post("/route_task_stream_start")
async def start_stream_task(request: StreamTaskRequest):
    try:
        stream_id = str(uuid.uuid4())
        store = get_stream_state_store()
        await store.create_stream(
            stream_id,
            metadata={
                "goblin": request.goblin,
                "task": request.task,
                "provider": request.provider or "auto",
                "model": request.model or "",
                "source": "legacy_api_router",
            },
        )

        async def _run_and_log() -> None:
            try:
                await run_task_stream_to_state(
                    stream_id=stream_id,
                    task_id=stream_id,
                    messages=_build_stream_messages(request),
                    provider=request.provider,
                    model=request.model,
                    metadata={
                        "goblin": request.goblin,
                        "task": request.task,
                        "source": "legacy_api_router",
                    },
                    initialize_state=False,
                )
            except Exception as exc:
                import structlog  # noqa: PLC0415

                structlog.get_logger().error(
                    "stream_task_background_failed",
                    stream_id=stream_id,
                    error=str(exc),
                )
                try:
                    _store = get_stream_state_store()
                    await _store.mark_status(
                        stream_id,
                        status="failed",
                        done=True,
                        updates={"error": str(exc)},
                    )
                except Exception as cleanup_exc:
                    structlog.get_logger().warning(
                        "stream_status_update_failed",
                        stream_id=stream_id,
                        error=str(cleanup_exc),
                    )

        asyncio.create_task(_run_and_log())
        return StreamResponse(stream_id=stream_id, status="started")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to start stream task: {exc}") from exc


@router.get("/route_task_stream_poll/{stream_id}")
async def poll_stream_task(stream_id: str):
    store = get_stream_state_store()
    stream = await store.poll_stream(stream_id)
    if stream is None:
        raise HTTPException(status_code=404, detail="Stream not found")
    return stream


@router.post("/route_task_stream_cancel/{stream_id}")
async def cancel_stream_task(stream_id: str):
    store = get_stream_state_store()
    cancelled = await store.cancel_stream(stream_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Stream not found")
    return {"stream_id": stream_id, "status": "cancelled"}


@router.get("/goblins")
async def get_goblins():
    inventory = await dispatcher.get_provider_inventory(include_hidden=False)
    goblins = []
    for provider in inventory:
        provider_id = str(provider.get("id", "unknown"))
        name = str(provider.get("name", provider_id))
        configured = bool(provider.get("configured"))
        healthy_value = provider.get("healthy")
        healthy = bool(healthy_value) if isinstance(healthy_value, bool) else False
        status = "available" if configured and healthy else "degraded"
        goblins.append(
            {
                "id": provider_id,
                "name": provider_id,
                "title": name,
                "status": status,
                "guild": str(provider.get("tier", "cloud")),
            }
        )
    return goblins


@router.get("/history/{goblin_id}")
async def get_goblin_history(goblin_id: str, limit: int = 10):
    capped_limit = max(1, min(int(limit), 100))
    store = await get_task_store()
    tasks = await store.list_tasks(limit=500)
    entries: List[Dict[str, Any]] = []
    for task in tasks:
        provider_id = (
            task.get("result", {}).get("selected_provider")
            if isinstance(task.get("result"), dict)
            else None
        )
        if provider_id and provider_id != goblin_id:
            continue
        payload = task.get("payload", {})
        entries.append(
            {
                "id": task.get("task_id", ""),
                "goblin": goblin_id,
                "task": payload.get("task", payload.get("prompt", task.get("task_type", "task"))),
                "response": (
                    task.get("result", {}).get("result", {}).get("text", "")
                    if isinstance(task.get("result"), dict)
                    else ""
                ),
                "timestamp": task.get("updated_at", task.get("created_at", time.time())),
                "kpis": f"status:{task.get('status', 'unknown')}",
            }
        )

    entries.extend(await _collect_chat_history_entries(goblin_id, limit=500))
    entries.sort(key=lambda item: _timestamp_sort_key(item.get("timestamp")))
    return entries[-capped_limit:]


@router.get("/stats/{goblin_id}")
async def get_goblin_stats(goblin_id: str):
    snapshot = routing_registry.snapshot()
    stats = snapshot.get(goblin_id, {})
    return {
        "goblin_id": goblin_id,
        "total_tasks": int(stats.get("success_rate", 0) * 100),
        "total_cost": stats.get("total_cost_usd", 0.0),
        "avg_duration_ms": stats.get("ewma_latency_ms", 0.0),
        "success_rate": stats.get("success_rate", 0.0),
        "last_active": stats.get("last_used", time.time()),
    }


@router.post("/orchestrate/parse")
async def parse_orchestration(request: ParseOrchestrationRequest):
    plan = parse_natural_language(request.text, request.default_goblin)
    plan_id = str(uuid.uuid4())
    steps = [
        {
            "id": step.goblin,
            "goblin": step.goblin,
            "task": step.task,
            "dependencies": step.dependencies,
        }
        for step in plan.steps
    ]
    store = await get_task_store()
    await store.save_task(
        plan_id,
        {
            "status": "pending",
            "task_type": "orchestration.plan",
            "payload": {"text": request.text, "default_goblin": request.default_goblin},
            "result": {
                "steps": steps,
                "complexity": plan.complexity,
                "estimated_duration": plan.estimated_duration,
            },
            "metadata": {"source": "orchestration.parse"},
        },
    )
    return {
        "plan_id": plan_id,
        "steps": steps,
        "complexity": plan.complexity,
        "estimated_duration": plan.estimated_duration,
        "max_parallel": 1,
    }


@router.post("/orchestrate/execute")
async def execute_orchestration(plan_id: str):
    store = await get_task_store()
    plan_task = await store.get_task(plan_id)
    if plan_task is None or plan_task.get("task_type") != "orchestration.plan":
        raise HTTPException(status_code=404, detail="Plan not found")

    steps = plan_task.get("result", {}).get("steps", [])
    execution_id = str(uuid.uuid4())
    pending_steps = [
        {
            **s,
            "status": "pending",
            "result": None,
            "provider_used": None,
            "cost_usd": 0.0,
            "duration_ms": 0,
            "error": None,
        }
        for s in steps
    ]
    await store.save_task(
        execution_id,
        {
            "status": "started",
            "task_type": "orchestration.execute",
            "payload": {"plan_id": plan_id},
            "result": {"steps": pending_steps, "total_cost": 0.0, "total_duration_ms": 0},
            "metadata": {"source": "orchestration.execute"},
        },
    )

    async def _run_and_log() -> None:
        try:
            await execute_orchestration_plan(
                execution_id=execution_id,
                plan_id=plan_id,
                steps=steps,
            )
        except Exception as exc:
            import structlog  # noqa: PLC0415

            structlog.get_logger().error(
                "orchestration_background_failed",
                execution_id=execution_id,
                plan_id=plan_id,
                error=str(exc),
            )
            try:
                _store = await get_task_store()
                await _store.update_task_status(
                    execution_id,
                    "failed",
                    result={
                        "steps": pending_steps,
                        "total_cost": 0.0,
                        "total_duration_ms": 0,
                        "error": str(exc),
                    },
                )
            except Exception as cleanup_exc:
                structlog.get_logger().warning(
                    "task_status_update_failed",
                    execution_id=execution_id,
                    error=str(cleanup_exc),
                )

    asyncio.create_task(_run_and_log())
    return {"execution_id": execution_id, "plan_id": plan_id, "status": "started"}


@router.get("/orchestrate/plans/{plan_id}")
async def get_orchestration_plan(plan_id: str):
    store = await get_task_store()
    tasks = await store.list_tasks(limit=500)
    matching = [
        task
        for task in tasks
        if task.get("task_type") == "orchestration.execute"
        and isinstance(task.get("payload"), dict)
        and task["payload"].get("plan_id") == plan_id
    ]
    if not matching:
        raise HTTPException(status_code=404, detail="Plan not found")
    task = matching[-1]
    return {
        "plan_id": plan_id,
        "status": task.get("status", "started"),
        "steps": task.get("result", {}).get("steps", [])
        if isinstance(task.get("result"), dict)
        else [],
        "total_cost": task.get("result", {}).get("total_cost", 0.0)
        if isinstance(task.get("result"), dict)
        else 0.0,
        "total_duration_ms": task.get("result", {}).get("total_duration_ms", 0)
        if isinstance(task.get("result"), dict)
        else 0,
        "created_at": task.get("created_at", time.time()),
    }
