from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from .api_models import (
    GenerateRequest,
    GenerateResponse,
    RouteTaskRequest,
    SimpleChatRequest,
    SimpleChatResponse,
    StreamResponse,
    StreamTaskRequest,
)
from .api_router_pkg import (
    build_stream_messages as _build_stream_messages_helper,
)
from .api_router_pkg import (
    collect_chat_history_entries as _collect_chat_history_entries_helper,
)
from .api_router_pkg import extract_result_text as _extract_result_text_helper
from .api_router_pkg import run_stream_task_background as _run_stream_task_background_helper
from .api_router_pkg import timestamp_sort_key as _timestamp_sort_key_helper
from .core.orchestration import parse_natural_language
from .input_validation import InputSanitizer
from .orchestration_router import router as orchestration_router
from .providers.dispatcher import dispatcher, invoke_provider
from .providers.dispatcher_pkg.execution import mock_fallback_enabled
from .routing.feedback_router import router as _feedback_router
from .routing.router import registry as routing_registry
from .routing.router import route_task as route_task_runtime
from .services.stream_state_store import get_stream_state_store
from .services.task_streaming import run_task_stream_to_state
from .storage.tasks import get_task_store

# Backward-compatible alias preserved for tests/integrations still patching
# `api.api_router.create_simple_orchestration_plan`.
create_simple_orchestration_plan = parse_natural_language

router = APIRouter(prefix="/api", tags=["api"])
router.include_router(orchestration_router)
router.include_router(_feedback_router)


def _build_stream_messages(request: StreamTaskRequest) -> List[Dict[str, str]]:
    return _build_stream_messages_helper(request)


def _extract_result_text(response: Dict[str, Any]) -> str:
    return _extract_result_text_helper(response)


def _timestamp_sort_key(value: Any) -> float:
    return _timestamp_sort_key_helper(value)


def _response_error_message(response: Any) -> str:
    if isinstance(response, dict):
        return str(
            response.get("error")
            or response.get("detail")
            or response.get("message")
            or "Request failed"
        )
    return str(response)


def _is_disallowed_mock_response(response: Any) -> bool:
    return (
        isinstance(response, dict)
        and str(response.get("provider", "")).strip().lower() == "mock"
        and not mock_fallback_enabled()
    )


async def _run_stream_task_background(stream_id: str, request: StreamTaskRequest) -> None:
    await _run_stream_task_background_helper(
        stream_id,
        request,
        run_stream_fn=run_task_stream_to_state,
        store_getter=get_stream_state_store,
    )


async def _collect_chat_history_entries(goblin_id: str, limit: int = 500) -> List[Dict[str, Any]]:
    return await _collect_chat_history_entries_helper(goblin_id, limit=limit)


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
        if _is_disallowed_mock_response(response):
            return SimpleChatResponse(ok=False, error="no-configured-providers")
        if isinstance(response, dict) and response.get("ok"):
            text = _extract_result_text(response)
            result_data = response.get("result", {})
            return SimpleChatResponse(
                ok=True,
                result={"text": text} if text else result_data,
                provider=str(response.get("provider", "unknown")),
                model=str(response.get("model", "unknown")),
            )
        return SimpleChatResponse(ok=False, error=_response_error_message(response))
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
        if _is_disallowed_mock_response(response):
            return GenerateResponse(error="no-configured-providers")
        if isinstance(response, dict) and response.get("ok"):
            text = _extract_result_text(response)
            return GenerateResponse(
                content=text,
                choices=[{"message": {"role": "assistant", "content": text}}],
            )
        return GenerateResponse(error=_response_error_message(response))
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
        asyncio.create_task(_run_stream_task_background(stream_id, request))
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
