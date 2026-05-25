"""Conversation archiving orchestration for long chat histories."""

from __future__ import annotations

import asyncio
import uuid
from typing import List

import structlog

from . import _runtime as _cr
from .constants import (
    CHAT_ARCHIVE_MAX_SOURCE_CHARS,
    CHAT_ARCHIVE_RETAIN_LAST,
    CHAT_ARCHIVE_SUMMARY_MODEL,
    CHAT_ARCHIVE_THRESHOLD,
)

logger = structlog.get_logger()

_archive_inflight: set[str] = set()
_archive_lock = asyncio.Lock()


async def schedule_conversation_archive(conversation_id: str) -> None:
    """Spawn non-blocking archive task if this conversation needs processing."""
    if not conversation_id:
        return

    try:
        async with _archive_lock:
            if conversation_id in _archive_inflight:
                return
            _archive_inflight.add(conversation_id)
    except Exception as exc:
        logger.warning("archive_lock_failed", conversation_id=conversation_id, error=str(exc))
        return

    async def _runner() -> None:
        try:
            await _maybe_archive_conversation(conversation_id)
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning(
                "conversation_archive_failed",
                conversation_id=conversation_id,
                error=str(exc),
            )
        finally:
            async with _archive_lock:
                _archive_inflight.discard(conversation_id)

    try:
        asyncio.create_task(_runner())
    except Exception as exc:
        logger.warning(
            "archive_task_spawn_failed",
            conversation_id=conversation_id,
            error=str(exc),
        )
        async with _archive_lock:
            _archive_inflight.discard(conversation_id)


async def _maybe_archive_conversation(conversation_id: str) -> None:
    threshold = max(2, CHAT_ARCHIVE_THRESHOLD)
    retain_last = max(1, CHAT_ARCHIVE_RETAIN_LAST)

    conversation = await _cr.conversation_store.get_conversation(conversation_id)
    if not conversation:
        return

    messages = list(conversation.messages)
    if len(messages) < threshold or len(messages) <= retain_last:
        return

    to_archive = messages[:-retain_last]
    if not to_archive:
        return

    archive_ids = [message.message_id for message in to_archive]
    summary_text = await _summarize_messages(to_archive)
    if not summary_text:
        logger.warning("conversation_archive_empty_summary", conversation_id=conversation_id)
        return

    min_ts = min(message.timestamp for message in to_archive)
    max_ts = max(message.timestamp for message in to_archive)
    summary_metadata = {
        "archived_summary": True,
        "archived_message_count": len(to_archive),
        "archive_window_start": min_ts.isoformat(),
        "archive_window_end": max_ts.isoformat(),
    }

    archived = await _cr.conversation_store.archive_messages(
        conversation_id=conversation_id,
        message_ids=archive_ids,
        summary_content=summary_text,
        summary_metadata=summary_metadata,
        summary_message_id=str(uuid.uuid4()),
        summary_timestamp=max_ts,
    )

    if archived:
        logger.info(
            "conversation_archived",
            conversation_id=conversation_id,
            archived_count=len(to_archive),
            retained_count=retain_last,
        )


async def _summarize_messages(messages: List) -> str:
    prompt = _build_summary_prompt(messages)
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "model": CHAT_ARCHIVE_SUMMARY_MODEL,
        "temperature": 0.2,
        "max_tokens": 220,
    }

    provider_response = await _cr.invoke_provider(
        pid=None,
        model=CHAT_ARCHIVE_SUMMARY_MODEL,
        payload=payload,
        timeout_ms=30000,
        stream=False,
    )

    if isinstance(provider_response, dict) and provider_response.get("ok"):
        return str(provider_response.get("result", {}).get("text", "")).strip()

    if isinstance(provider_response, dict) and "choices" in provider_response:
        choices = provider_response.get("choices") or []
        if choices:
            return str(choices[0].get("message", {}).get("content", "")).strip()

    logger.warning("conversation_archive_summary_provider_error", response=provider_response)
    return ""


def _build_summary_prompt(messages: List) -> str:
    lines: List[str] = []
    for message in messages:
        role = getattr(message, "role", "unknown")
        content = getattr(message, "content", "")
        if content:
            lines.append(f"{role}: {content}")

    source_text = "\n".join(lines)
    if CHAT_ARCHIVE_MAX_SOURCE_CHARS > 0 and len(source_text) > CHAT_ARCHIVE_MAX_SOURCE_CHARS:
        source_text = source_text[:CHAT_ARCHIVE_MAX_SOURCE_CHARS]

    return (
        "Summarize this archived chat segment in 1-2 concise sentences. "
        "Focus on durable facts, decisions, and unresolved asks.\n\n"
        f"Conversation segment:\n{source_text}\n\n"
        "Summary:"
    )
