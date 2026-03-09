from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
import time
import logging

from .providers.dispatcher import invoke_provider

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
    """Generate server-sent events for task streaming using real provider"""
    # Send initial status
    yield f"data: {json.dumps({'status': 'started', 'task_id': task_id})}\n\n"

    accumulated_text = ""
    total_tokens = 0
    total_cost = 0.0
    used_provider = provider or "unknown"
    used_model = model or "unknown"
    start_time = time.time()

    try:
        # Build payload
        payload = {"messages": messages, "model": model}

        # Invoke provider with streaming
        provider_response = await invoke_provider(
            pid=provider,
            model=model,
            payload=payload,
            timeout_ms=30000,
            stream=True,
        )

        if not isinstance(provider_response, dict) or not provider_response.get("ok"):
            # Provider returned an error — fall back to non-streaming
            provider_response = await invoke_provider(
                pid=provider,
                model=model,
                payload=payload,
                timeout_ms=30000,
                stream=False,
            )
            if isinstance(provider_response, dict) and provider_response.get("ok"):
                result_data = provider_response.get("result", {})
                accumulated_text = result_data.get("text", str(provider_response))
                used_provider = provider_response.get("provider", used_provider)
                used_model = provider_response.get("model", used_model)
                yield f"data: {json.dumps({'content': accumulated_text, 'token_count': 0, 'cost_delta': 0, 'done': False})}\n\n"
            else:
                error_msg = provider_response.get("error", "unknown-error") if isinstance(provider_response, dict) else "provider-error"
                yield f"data: {json.dumps({'error': error_msg, 'done': True})}\n\n"
                return

        elif provider_response.get("stream"):
            # Real streaming path — consume async generator from provider
            stream_gen = provider_response["stream"]
            async for chunk in stream_gen:
                chunk_text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
                if not chunk_text:
                    continue
                accumulated_text += chunk_text
                token_estimate = max(1, len(chunk_text) // 4)
                total_tokens += token_estimate
                yield f"data: {json.dumps({'content': chunk_text, 'token_count': token_estimate, 'cost_delta': 0, 'done': False})}\n\n"
        else:
            # Provider returned ok but no stream key — extract text directly
            result_data = provider_response.get("result", {})
            accumulated_text = result_data.get("text", "")
            used_provider = provider_response.get("provider", used_provider)
            used_model = provider_response.get("model", used_model)
            if accumulated_text:
                yield f"data: {json.dumps({'content': accumulated_text, 'token_count': 0, 'cost_delta': 0, 'done': False})}\n\n"

        duration_ms = int((time.time() - start_time) * 1000)

        # Send completion event
        yield f"data: {json.dumps({'result': accumulated_text, 'cost': total_cost, 'tokens': total_tokens, 'model': used_model, 'provider': used_provider, 'duration_ms': duration_ms, 'task_id': task_id, 'done': True})}\n\n"

    except Exception as exc:
        logger.error(f"Streaming error for task {task_id}: {exc}")
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
        logger.error(f"Stream task failed: {e}")
        raise HTTPException(status_code=500, detail="Task streaming failed")
