"""Helper functions extracted from the legacy API router."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List


def extract_result_text(response: Dict[str, Any]) -> str:
    result_data = response.get("result", {})
    if isinstance(result_data, dict):
        text = result_data.get("text")
        if isinstance(text, str) and text:
            return text
    fallback_text = response.get("text")
    if isinstance(fallback_text, str):
        return fallback_text
    return ""


def build_stream_messages(request: Any) -> List[Dict[str, str]]:
    payload_lines = [request.task.strip()]
    if request.code:
        payload_lines.append("\nCode:\n" + request.code.strip())
    user_message = "\n".join(line for line in payload_lines if line)
    return [{"role": "user", "content": user_message}]


def timestamp_sort_key(value: Any) -> float:
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


async def run_stream_task_background(
    stream_id: str,
    request: Any,
    *,
    run_stream_fn,
    store_getter,
) -> None:
    try:
        await run_stream_fn(
            stream_id=stream_id,
            task_id=stream_id,
            messages=build_stream_messages(request),
            provider=request.provider,
            model=request.model,
            metadata={
                "goblin": request.goblin,
                "task": request.task,
                "source": "legacy_api_router",
            },
            initialize_state=False,
        )
    except Exception as exc:  # noqa: BLE001
        import structlog  # noqa: PLC0415

        structlog.get_logger().error(
            "stream_task_background_failed",
            stream_id=stream_id,
            error=str(exc),
        )
        try:
            _store = store_getter()
            await _store.mark_status(
                stream_id,
                status="failed",
                done=True,
                updates={"error": str(exc)},
            )
        except Exception as cleanup_exc:  # noqa: BLE001
            structlog.get_logger().warning(
                "stream_status_update_failed",
                stream_id=stream_id,
                error=str(cleanup_exc),
            )


async def collect_chat_history_entries(goblin_id: str, limit: int = 500) -> List[Dict[str, Any]]:
    from ..storage import conversation_store

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
