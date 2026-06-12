"""Background orchestration executor: runs each step of a parsed plan via route_task."""

from __future__ import annotations

import time
from typing import Any, Dict, List

import structlog

from ..routing.router import route_task
from ..storage.tasks import get_task_store

logger = structlog.get_logger()


def _topological_order(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return steps sorted so that each step comes after its dependencies."""
    by_goblin = {s["goblin"]: s for s in steps}
    visited: set[str] = set()
    result: List[Dict[str, Any]] = []

    def visit(step: Dict[str, Any]) -> None:
        goblin = step["goblin"]
        if goblin in visited:
            return
        visited.add(goblin)
        for dep in step.get("dependencies", []):
            if dep in by_goblin:
                visit(by_goblin[dep])
        result.append(step)

    for step in steps:
        visit(step)
    return result


async def execute_orchestration_plan(
    execution_id: str,
    plan_id: str,
    steps: List[Dict[str, Any]],
) -> None:
    """Execute an orchestration plan step-by-step, persisting results to the task store.

    Each step is routed to the best available provider via route_task with the "chat"
    capability. Results from dependency steps are passed as system context so later steps
    can build on earlier ones. Failed steps are recorded but do not abort remaining
    independent steps.
    """
    store = await get_task_store()
    start_time = time.time()

    step_results: List[Dict[str, Any]] = [
        {
            "id": step.get("id", step["goblin"]),
            "goblin": step["goblin"],
            "task": step["task"],
            "dependencies": step.get("dependencies", []),
            "status": "pending",
            "result": None,
            "provider_used": None,
            "cost_usd": 0.0,
            "duration_ms": 0,
            "error": None,
        }
        for step in steps
    ]

    total_cost = 0.0

    await store.update_task_status(
        execution_id,
        "running",
        result={
            "steps": step_results,
            "total_cost": 0.0,
            "total_duration_ms": 0,
        },
    )

    ordered = _topological_order(steps)
    step_context: Dict[str, str] = {}

    for step in ordered:
        goblin = step["goblin"]
        idx = next((i for i, s in enumerate(step_results) if s["goblin"] == goblin), None)
        if idx is None:
            continue

        step_results[idx]["status"] = "running"
        await store.update_task_status(
            execution_id,
            "running",
            result={
                "steps": step_results,
                "total_cost": total_cost,
                "total_duration_ms": int((time.time() - start_time) * 1000),
            },
        )

        messages: List[Dict[str, str]] = [{"role": "user", "content": step["task"]}]
        dep_context = "\n\n".join(
            step_context[dep] for dep in step.get("dependencies", []) if dep in step_context
        )
        if dep_context:
            messages.insert(
                0,
                {"role": "system", "content": f"Context from previous steps:\n{dep_context}"},
            )

        step_start = time.time()
        try:
            result = await route_task(
                task_type="chat",
                payload={"messages": messages},
                prefer_cost=True,
                max_retries=2,
            )
            step_duration_ms = int((time.time() - step_start) * 1000)

            if result.get("ok"):
                inner = result.get("result") or {}
                result_text = inner.get("text", "") if isinstance(inner, dict) else str(inner)
                cost = float((inner.get("cost_usd") or 0.0) if isinstance(inner, dict) else 0.0)
                provider_used = (
                    result.get("selected_provider") or result.get("provider") or "unknown"
                )

                step_results[idx].update(
                    {
                        "status": "completed",
                        "result": result_text,
                        "provider_used": provider_used,
                        "cost_usd": cost,
                        "duration_ms": step_duration_ms,
                    }
                )
                step_context[goblin] = result_text
                total_cost += cost
            else:
                error = result.get("error", "Step failed")
                step_results[idx].update(
                    {"status": "failed", "error": error, "duration_ms": step_duration_ms}
                )
                logger.warning(
                    "orchestration_step_failed",
                    execution_id=execution_id,
                    goblin=goblin,
                    error=error,
                )
        except Exception as exc:
            step_duration_ms = int((time.time() - step_start) * 1000)
            step_results[idx].update(
                {"status": "failed", "error": str(exc), "duration_ms": step_duration_ms}
            )
            logger.error(
                "orchestration_step_exception",
                execution_id=execution_id,
                goblin=goblin,
                error=str(exc),
            )

        await store.update_task_status(
            execution_id,
            "running",
            result={
                "steps": step_results,
                "total_cost": total_cost,
                "total_duration_ms": int((time.time() - start_time) * 1000),
            },
        )

    failed = [s for s in step_results if s["status"] == "failed"]
    final_status = "failed" if failed else "completed"
    total_duration_ms = int((time.time() - start_time) * 1000)

    await store.update_task_status(
        execution_id,
        final_status,
        result={
            "steps": step_results,
            "total_cost": total_cost,
            "total_duration_ms": total_duration_ms,
        },
    )

    logger.info(
        "orchestration_execution_complete",
        execution_id=execution_id,
        plan_id=plan_id,
        status=final_status,
        total_cost=total_cost,
        total_duration_ms=total_duration_ms,
        step_count=len(steps),
        failed_steps=len(failed),
    )
