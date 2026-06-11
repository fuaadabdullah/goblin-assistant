"""Post-response stage: persist the assistant message, record task/usage
events, and schedule fire-and-forget learning tasks."""

import uuid
from importlib import import_module
from typing import Any, Dict, Optional

import structlog

from .. import _runtime as _cr
from .usage_tracker import (
    emit_chat_message_created,
    record_chat_completion_task,
    record_usage_event,
)

logger = structlog.get_logger()

_messages_pkg = import_module(__package__)


async def persist_assistant_message(
    *,
    conversation_id: str,
    current_user: Any,
    response_content: str,
    used_provider: str,
    used_model: Optional[str],
    context_metadata: Dict[str, Any],
    usage: Optional[dict],
    cost_usd: Optional[float],
    correlation_id: Optional[str],
) -> str:
    """Persist the assistant message (best-effort) and return its message id."""
    response_message_id = str(uuid.uuid4())
    assistant_metadata: Dict[str, Any] = {
        "provider": used_provider,
        "model": used_model,
        "message_id": response_message_id,
    }
    if context_metadata:
        assistant_metadata.update(context_metadata)
    if usage:
        assistant_metadata["usage"] = usage
    if cost_usd is not None:
        assistant_metadata["cost_usd"] = cost_usd
    if correlation_id:
        assistant_metadata["correlation_id"] = correlation_id

    asst_msg_saved = await _cr.conversation_store.add_message_to_conversation(
        conversation_id=conversation_id,
        role="assistant",
        content=response_content,
        metadata=assistant_metadata,
        message_id=response_message_id,
    )
    if not asst_msg_saved:
        logger.warning(
            "failed to persist assistant message",
            conversation_id=conversation_id,
            message_id=response_message_id,
        )
    else:
        await emit_chat_message_created(
            current_user=current_user,
            conversation_id=conversation_id,
            message_id=response_message_id,
            role="assistant",
            has_attachments=False,
            correlation_id=correlation_id,
            provider=used_provider,
            model=used_model,
        )
        await _messages_pkg.schedule_conversation_archive(conversation_id)

    return response_message_id


async def record_completion_artifacts(
    *,
    current_user: Any,
    conversation_id: str,
    user_message_id: Optional[str],
    response_message_id: str,
    sanitized_message: str,
    response_content: str,
    used_provider: str,
    used_model: Optional[str],
    usage: Optional[dict],
    cost_usd: Optional[float],
    correlation_id: Optional[str],
) -> None:
    """Record task history + usage event (both best-effort)."""
    try:
        await record_chat_completion_task(
            user_id=current_user.id,
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            assistant_message_id=response_message_id,
            user_message=sanitized_message,
            assistant_message=response_content,
            provider=used_provider,
            model=used_model,
            usage=usage,
            cost_usd=cost_usd,
        )
    except Exception as task_err:
        logger.warning(
            "chat_completion_task_history_write_failed",
            conversation_id=conversation_id,
            message_id=response_message_id,
            error=str(task_err),
        )

    try:
        await record_usage_event(
            user_id=current_user.id,
            conversation_id=conversation_id,
            message_id=response_message_id,
            provider=used_provider,
            model=used_model,
            usage=usage,
            cost_usd=cost_usd,
            correlation_id=correlation_id,
        )
    except Exception as usage_err:
        logger.warning(
            "usage_event_write_failed",
            conversation_id=conversation_id,
            message_id=response_message_id,
            error=str(usage_err),
        )


def schedule_preference_learning(
    *,
    current_user: Any,
    used_provider: str,
    used_model: Optional[str],
    intent_meta: dict,
    usage: Optional[dict],
) -> None:
    """Fire-and-forget preference learning update."""
    try:
        import asyncio as _asyncio  # noqa: PLC0415

        from api.services.preference_learner import preference_learner as _pl  # noqa: PLC0415

        _pref_task = _asyncio.create_task(
            _pl.record_response(
                user_id=str(current_user.id),
                provider_id=used_provider,
                model=used_model,
                intent_label=intent_meta.get("label", "unknown"),
                completion_tokens=int(
                    (usage or {}).get("completion_tokens")
                    or (usage or {}).get("output_tokens")
                    or 0
                ),
                explicit_rating=None,
            )
        )
        _pref_task.add_done_callback(lambda _t: None)
    except Exception:
        pass


def _last_assistant_index(history_messages: list) -> int:
    for i in range(len(history_messages) - 1, -1, -1):
        if history_messages[i].get("role") == "assistant":
            return i
    return -1


def _message_id_at(conversation: Any, index: int) -> Optional[str]:
    if hasattr(conversation, "messages") and index < len(conversation.messages):
        msg_obj = conversation.messages[index]
        if hasattr(msg_obj, "message_id"):
            return msg_obj.message_id
    return None


def schedule_feedback_outcomes(
    *,
    current_user: Any,
    conversation: Any,
    conversation_id: str,
    history_messages: list,
    response_message_id: str,
    correlation_id: Optional[str],
    resolved_department: str,
    used_provider: str,
    used_model: Optional[str],
    task_type: str,
    intent_meta: dict,
    complexity_score: Any,
) -> None:
    """Fire-and-forget feedback-outcome tracking (continuation + provider switch)."""
    try:
        import asyncio as _asyncio  # noqa: PLC0415

        from api.services.feedback_service import (  # noqa: PLC0415
            FeedbackContext,
            feedback_service,
        )

        # 1. Detect continuation: find the previous assistant message and mark it
        #    as having had the conversation continue after it
        if len(history_messages) >= 2:
            prev_idx = _last_assistant_index(history_messages[:-1])
            if prev_idx >= 0:
                prev_asst_msg_id = _message_id_at(conversation, prev_idx)
                if prev_asst_msg_id:
                    context = FeedbackContext(
                        user_id=str(current_user.id),
                        conversation_id=conversation_id,
                        message_id=prev_asst_msg_id,
                        request_id=correlation_id,
                        department=resolved_department,
                        provider=used_provider,
                        model=used_model,
                        task_type=task_type,
                        intent_label=intent_meta.get("label"),
                        complexity_score=complexity_score,
                    )
                    _prev_task = _asyncio.create_task(
                        feedback_service.record_conversation_continued(
                            context=context,
                            next_message_id=response_message_id,
                        )
                    )
                    _prev_task.add_done_callback(lambda _t: None)

        # 2. Detect provider/model switch against the previous assistant message
        if len(history_messages) >= 2:
            switch_idx = _last_assistant_index(history_messages)
            prev_provider = None
            prev_model = None
            if (
                switch_idx >= 0
                and hasattr(conversation, "messages")
                and switch_idx < len(conversation.messages)
            ):
                prev_msg_obj = conversation.messages[switch_idx]
                if hasattr(prev_msg_obj, "metadata_") and prev_msg_obj.metadata_:
                    prev_provider = prev_msg_obj.metadata_.get("provider")
                    prev_model = prev_msg_obj.metadata_.get("model")

            if prev_provider and prev_provider != used_provider:
                switch_asst_msg_id = _message_id_at(conversation, switch_idx)
                if switch_asst_msg_id:
                    switch_context = FeedbackContext(
                        user_id=str(current_user.id),
                        conversation_id=conversation_id,
                        message_id=switch_asst_msg_id,
                        request_id=correlation_id,
                        department=resolved_department,
                        provider=prev_provider,
                        model=prev_model,
                        task_type=task_type,
                        intent_label=intent_meta.get("label"),
                        complexity_score=complexity_score,
                        previous_provider=prev_provider,
                        previous_model=prev_model,
                    )
                    _switch_task = _asyncio.create_task(
                        feedback_service.record_provider_switch(
                            context=switch_context,
                            new_provider=used_provider,
                            new_model=used_model,
                        )
                    )
                    _switch_task.add_done_callback(lambda _t: None)

        # 3. Regeneration is better detected from the frontend sending a flag.

    except Exception as exc:
        logger.debug("feedback_outcome_tracking_failed error=%s", exc)
