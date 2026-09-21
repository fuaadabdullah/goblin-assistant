from __future__ import annotations

import time
from typing import Any, AsyncIterator, Dict, List, Optional

import structlog

from ..providers.dispatcher import dispatcher as provider_dispatcher
from ..providers.dispatcher import invoke_provider
from ..providers.quota_pkg.estimation import estimate_text_tokens
from .stream_state_store import get_stream_state_store

logger = structlog.get_logger()


def _extract_result_text(provider_response: Dict[str, Any]) -> str:
    result_data = provider_response.get("result", {})
    if isinstance(result_data, dict):
        text = result_data.get("text")
        if isinstance(text, str):
            return text
    top_level_text = provider_response.get("text")
    if isinstance(top_level_text, str):
        return top_level_text
    return ""

def _extract_result_usage(provider_response: Dict[str, Any]) -> tuple[Dict[str, Any], float]:
    result_data = provider_response.get("result", {})
    if not isinstance(result_data, dict):
        return {}, 0.0
    usage = result_data.get("usage", {})
    normalized_usage = usage if isinstance(usage, dict) else {}
    try:
        cost = float(result_data.get("cost_usd") or provider_response.get("cost_usd") or 0.0)
    except (TypeError, ValueError):
        cost = 0.0
    return normalized_usage, max(0.0, cost)


def _usage_output_tokens(usage: Dict[str, Any]) -> int:
    return max(
        0,
        int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
    )


def _estimate_provider_cost(
    provider_id: str,
    model: str,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> float:
    if provider_id in {"", "auto", "none"}:
        return 0.0
    try:
        provider = provider_dispatcher.get_provider(provider_id)
        estimate = getattr(provider, "estimate_cost", None)
        if not callable(estimate):
            return 0.0
        return max(
            0.0,
            float(
                estimate(
                    max(0, input_tokens),
                    max(0, output_tokens),
                    model=model or None,
                )
            ),
        )
    except Exception:
        return 0.0



async def iter_task_stream_chunks(  # noqa: PLR0915
    *,
    task_id: str,
    messages: List[Dict[str, str]],
    provider: Optional[str],
    model: Optional[str],
) -> AsyncIterator[Dict[str, Any]]:
    accumulated_text = ""
    total_tokens = 0
    total_cost = 0.0
    selected_provider = provider or "auto"
    selected_model = model or ""
    input_tokens = sum(
        estimate_text_tokens(str(message.get("content", "") or ""))
        for message in messages
    )
    start_time = time.time()

    payload = {"messages": messages, "model": model}
    provider_response = await invoke_provider(
        pid=selected_provider,
        model=model,
        payload=payload,
        timeout_ms=30000,
        stream=True,
    )

    if not isinstance(provider_response, dict) or not provider_response.get("ok"):
        fallback = await invoke_provider(
            pid=selected_provider,
            model=model,
            payload=payload,
            timeout_ms=30000,
            stream=False,
        )
        if isinstance(fallback, dict) and fallback.get("ok"):
            text = _extract_result_text(fallback)
            selected_provider = str(fallback.get("provider") or selected_provider)
            selected_model = str(fallback.get("model") or selected_model)
            usage, reported_cost = _extract_result_usage(fallback)
            token_count = _usage_output_tokens(usage) or estimate_text_tokens(text)
            total_tokens = token_count
            total_cost = reported_cost or _estimate_provider_cost(
                selected_provider,
                selected_model,
                input_tokens=input_tokens,
                output_tokens=token_count,
            )
            if text:
                yield {
                    "content": text,
                    "token_count": token_count,
                    "cost_delta": total_cost,
                    "done": False,
                }
                accumulated_text = text
        else:
            error_msg = (
                fallback.get("error", "unknown-error")
                if isinstance(fallback, dict)
                else "provider-error"
            )
            yield {"error": str(error_msg), "done": True}
            return
    elif provider_response.get("stream"):
        selected_provider = str(provider_response.get("provider") or selected_provider)
        selected_model = str(provider_response.get("model") or selected_model)
        stream_gen = provider_response["stream"]
        pending_input_cost = _estimate_provider_cost(
            selected_provider,
            selected_model,
            input_tokens=input_tokens,
        )
        total_cost += pending_input_cost

        async for chunk in stream_gen:
            chunk_text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
            if not chunk_text:
                continue
            token_estimate = estimate_text_tokens(chunk_text)
            output_cost = _estimate_provider_cost(
                selected_provider,
                selected_model,
                output_tokens=token_estimate,
            )
            cost_delta = pending_input_cost + output_cost
            pending_input_cost = 0.0
            accumulated_text += chunk_text
            total_tokens += token_estimate
            total_cost += output_cost
            yield {
                "content": chunk_text,
                "token_count": token_estimate,
                "cost_delta": cost_delta,
                "done": False,
            }
    else:
        text = _extract_result_text(provider_response)
        selected_provider = str(provider_response.get("provider") or selected_provider)
        selected_model = str(provider_response.get("model") or selected_model)
        usage, reported_cost = _extract_result_usage(provider_response)
        token_count = _usage_output_tokens(usage) or estimate_text_tokens(text)
        total_tokens = token_count
        total_cost = reported_cost or _estimate_provider_cost(
            selected_provider,
            selected_model,
            input_tokens=input_tokens,
            output_tokens=token_count,
        )
        if text:
            accumulated_text = text
            yield {
                "content": text,
                "token_count": token_count,
                "cost_delta": total_cost,
                "done": False,
            }

    duration_ms = int((time.time() - start_time) * 1000)
    yield {
        "result": accumulated_text,
        "cost": total_cost,
        "tokens": total_tokens,
        "model": selected_model,
        "provider": selected_provider,
        "duration_ms": duration_ms,
        "task_id": task_id,
        "done": True,
    }


async def run_task_stream_to_state(  # noqa: PLR0913
    *,
    stream_id: str,
    task_id: str,
    messages: List[Dict[str, str]],
    provider: Optional[str],
    model: Optional[str],
    metadata: Optional[Dict[str, Any]] = None,
    initialize_state: bool = True,
) -> None:
    store = get_stream_state_store()
    if initialize_state:
        await store.create_stream(
            stream_id,
            metadata={
                "task_id": task_id,
                "provider": provider or "auto",
                "model": model or "",
                **(metadata or {}),
            },
        )

    try:
        async for chunk in iter_task_stream_chunks(
            task_id=task_id,
            messages=messages,
            provider=provider,
            model=model,
        ):
            await store.append_chunk(stream_id, chunk)
            if chunk.get("done") is True:
                if chunk.get("error"):
                    await store.mark_status(
                        stream_id,
                        status="failed",
                        done=True,
                        updates={"error": chunk.get("error")},
                    )
                else:
                    await store.mark_status(stream_id, status="completed", done=True)
                return
        await store.mark_status(stream_id, status="completed", done=True)
    except Exception as exc:
        logger.error("task_stream_execution_failed", stream_id=stream_id, error=str(exc))
        await store.append_chunk(stream_id, {"error": "Streaming failed", "done": True})
        await store.mark_status(
            stream_id,
            status="failed",
            done=True,
            updates={"error": str(exc)},
        )
