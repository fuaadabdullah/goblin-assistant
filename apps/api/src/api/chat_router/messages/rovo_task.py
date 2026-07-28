"""Rovo Dev task lifecycle helpers for the chat pipeline."""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger()


async def create_rovo_task(
    resolved_provider: str,
    prompt: str,
    conversation_id: str,
    user_id: str,
    complexity_score: Optional[float],
    intent_meta: Dict[str, Any],
) -> Optional[str]:
    """Create a Rovo Dev task record and return its task_id, or None on failure."""
    if resolved_provider != "rovo_dev":
        return None
    try:
        from ...storage.tasks import task_store  # noqa: PLC0415

        task_id = str(uuid.uuid4())
        await task_store.save_task(
            task_id,
            {
                "task_id": task_id,
                "task_type": "code",
                "status": "pending",
                "payload": {
                    "prompt": prompt,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                },
                "metadata": {
                    "provider": "rovo_dev",
                    "intent": intent_meta,
                    "complexity_score": complexity_score,
                },
            },
        )
        return task_id
    except Exception as exc:
        logger.warning("rovo_dev_task_create_failed", error=str(exc))
        return None


async def update_rovo_task(task_id: Optional[str], provider_response: Any) -> None:
    """Update Rovo Dev task status from the provider response."""
    if task_id is None:
        return
    try:
        from ...storage.tasks import task_store  # noqa: PLC0415

        is_ok = isinstance(provider_response, dict) and provider_response.get("ok")
        await task_store.update_task_status(
            task_id,
            "completed" if is_ok else "failed",
            result={
                "diff": (
                    provider_response.get("result", {}).get("text") or provider_response.get("text")
                )
                if isinstance(provider_response, dict)
                else None,
                "error": provider_response.get("error")
                if isinstance(provider_response, dict)
                else None,
                "latency_ms": provider_response.get("latency_ms")
                if isinstance(provider_response, dict)
                else None,
            },
        )
    except Exception as exc:
        logger.warning("rovo_dev_task_update_failed", task_id=task_id, error=str(exc))
