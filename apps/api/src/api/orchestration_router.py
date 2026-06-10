"""
Orchestration endpoints — parse, execute, and inspect orchestration plans.

Extracted from api_router.py. Included into api_router's /api prefix router,
so all routes here are served under /api/orchestrate/...
"""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, HTTPException

from .api_models import ParseOrchestrationRequest
from .core.orchestration import parse_natural_language
from .services.orchestration_executor import execute_orchestration_plan
from .storage.tasks import get_task_store

router = APIRouter()


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
    import time

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
