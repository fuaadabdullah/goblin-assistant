"""Usage tracking and event emission helpers — explicit side-effect boundary."""

import uuid
from importlib import import_module
from typing import Any, Dict, Optional

from ...core.contracts import ChatMessageCreatedPayload, ChatMessageFailedPayload

_messages_pkg = import_module(__package__)


def usage_token_breakdown(usage: Optional[Dict[str, Any]]) -> tuple[int, int, int]:
    """Extract prompt/completion/total tokens from a usage dict.

    Supports both OpenAI-style (prompt_tokens) and Anthropic-style
    (input_tokens) keys. Returns zeros for any missing value.
    """
    if not isinstance(usage, dict):
        return 0, 0, 0
    prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
    return max(0, prompt_tokens), max(0, completion_tokens), max(0, total_tokens)


async def record_chat_completion_task(
    *,
    user_id: str,
    conversation_id: str,
    user_message_id: str,
    assistant_message_id: str,
    user_message: str,
    assistant_message: str,
    provider: str,
    model: str,
    usage: Optional[Dict[str, Any]],
    cost_usd: Optional[float],
) -> None:
    """Persist a chat completion result as a task record.

    This is an explicit side-effect boundary — calls into task storage.
    """
    prompt_tokens, completion_tokens, total_tokens = usage_token_breakdown(usage)
    task_id = str(uuid.uuid4())
    task_store = await _messages_pkg.get_task_store()

    await task_store.save_task(
        task_id,
        {
            "task_id": task_id,
            "user_id": user_id,
            "status": "completed",
            "task_type": "chat.completion",
            "payload": {
                "task": user_message,
                "conversation_id": conversation_id,
                "user_message_id": user_message_id,
            },
            "result": {
                "selected_provider": provider,
                "model": model,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                },
                "cost_usd": float(cost_usd or 0.0),
                "result": {"text": assistant_message},
            },
            "metadata": {
                "source": "chat.send_message",
                "conversation_id": conversation_id,
                "assistant_message_id": assistant_message_id,
            },
        },
    )


async def record_usage_event(
    *,
    user_id: str,
    conversation_id: str,
    message_id: str,
    provider: str,
    model: str,
    usage: Optional[Dict[str, Any]],
    cost_usd: Optional[float],
    correlation_id: Optional[str],
) -> None:
    """Persist a usage event for billing/quota tracking.

    This is an explicit side-effect boundary — calls into usage event storage.
    """
    prompt_tokens, completion_tokens, total_tokens = usage_token_breakdown(usage)
    usage_store = await _messages_pkg.get_usage_event_store()
    await usage_store.save_event(
        {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "message_id": message_id,
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_usd": float(cost_usd or 0.0),
            "metadata": {
                "source": "chat.send_message",
                "correlation_id": correlation_id,
            },
        }
    )


async def emit_chat_message_failed(
    *,
    current_user: Any,
    conversation_id: str,
    stage: str,
    message_id: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    category: Optional[str] = None,
    code: Optional[str] = None,
    status_code: Optional[int] = None,
    error: Optional[str] = None,
    error_type: Optional[str] = None,
) -> None:
    """Emit a chat.message.failed event.

    This is an explicit side-effect boundary — fires an event through the
    event emitter.
    """

    await _messages_pkg.event_emitter.emit(
        "chat.message.failed",
        source="api.chat_router.messages",
        actor_user_id=current_user.id,
        payload=ChatMessageFailedPayload(
            conversation_id=conversation_id,
            message_id=message_id,
            stage=stage,
            provider=provider,
            model=model,
            category=category,
            code=code,
            status_code=status_code,
            error=error,
            error_type=error_type,
        ),
    )


async def emit_chat_message_created(
    *,
    current_user: Any,
    conversation_id: str,
    message_id: str,
    role: str,
    has_attachments: bool,
    correlation_id: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> None:
    """Emit a chat.message.created event.

    This is an explicit side-effect boundary — fires an event through the
    event emitter.
    """
    await _messages_pkg.event_emitter.emit(
        "chat.message.created",
        source="api.chat_router.messages",
        actor_user_id=current_user.id,
        correlation_id=correlation_id,
        payload=ChatMessageCreatedPayload(
            conversation_id=conversation_id,
            message_id=message_id,
            role=role,
            provider=provider,
            model=model,
            has_attachments=has_attachments,
        ),
    )
