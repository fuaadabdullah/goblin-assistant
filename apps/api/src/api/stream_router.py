import json
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .services.stream_state_store import get_stream_state_store
from .services.task_streaming import iter_task_stream_chunks

router = APIRouter(prefix="/stream", tags=["stream"])
logger = logging.getLogger(__name__)


class StreamTaskRequest(BaseModel):
    """Request model for streaming task execution"""

    task_id: str
    messages: List[Dict[str, str]]
    provider: Optional[str] = None
    model: Optional[str] = None


async def generate_stream_events(
    task_id: str,
    messages: List[Dict[str, str]],
    provider: str,
    model: str,
):
    """Generate server-sent events for task streaming using real provider."""
    # Send initial status
    yield f"data: {json.dumps({'status': 'started', 'task_id': task_id})}\n\n"
    store = get_stream_state_store()
    await store.create_stream(
        task_id,
        metadata={
            "task_id": task_id,
            "provider": provider or "auto",
            "model": model or "",
            "source": "stream_router",
        },
    )

    try:
        async for chunk in iter_task_stream_chunks(
            task_id=task_id,
            messages=messages,
            provider=provider,
            model=model,
        ):
            await store.append_chunk(task_id, chunk)
            yield f"data: {json.dumps(chunk)}\n\n"
            if chunk.get("done") is True:
                if chunk.get("error"):
                    await store.mark_status(
                        task_id,
                        status="failed",
                        done=True,
                        updates={"error": chunk.get("error")},
                    )
                else:
                    await store.mark_status(task_id, status="completed", done=True)
                return
        await store.mark_status(task_id, status="completed", done=True)
    except Exception as exc:
        logger.error("Streaming error for task %s: %s", task_id, exc)
        await store.append_chunk(task_id, {"error": "Streaming failed", "done": True})
        await store.mark_status(task_id, status="failed", done=True, updates={"error": str(exc)})
        yield f"data: {json.dumps({'error': 'Streaming failed', 'done': True})}\n\n"


@router.post("")
async def stream_task(request: StreamTaskRequest):
    """Stream task execution results using Server-Sent Events with real provider"""
    try:
        return StreamingResponse(
            generate_stream_events(
                task_id=request.task_id,
                messages=request.messages,
                provider=request.provider or "groq",
                model=request.model or "llama-3.3-70b-versatile",
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
            },
        )
    except Exception as e:
        logger.error("Stream task failed: %s", e)
        raise HTTPException(status_code=500, detail="Task streaming failed")
