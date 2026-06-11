"""SSE streaming endpoint + the generator that powers it.

The generator persists the user message *before* calling the provider so a
provider failure still leaves the conversation history intact. Error events
carry an `is_recoverable` flag so the client knows whether to retry.
"""

import asyncio
import time
import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..auth.router import User as AuthenticatedUser
from ..auth.router import get_current_user
from ..core.contracts import ChatMessageCreatedPayload
from ..observability.events import event_emitter
from ..storage.tasks import get_task_store
from ..storage.usage_events import get_usage_event_store
from . import _runtime as _cr
from .archiving import schedule_conversation_archive
from .helpers import _format_sse_event
from .schemas import StreamChatRequest

logger = structlog.get_logger()

router = APIRouter()


async def generate_chat_stream(
    message: str,
    conversation_id: str,
    current_user: AuthenticatedUser,
    provider: Optional[str] = None,
    model: Optional[str] = None,
):
    """Generate server-sent events for chat streaming via real provider.

    Error handling:
    - Auth errors (401): sent immediately, is_recoverable=false
    - Provider timeouts: error event, is_recoverable=true (user message saved)
    - Provider errors: attempt non-streaming fallback, then error event
    - DB write failures (user msg): error event, is_recoverable=true
    - Stream interruptions: error event with partial-response preview
    """
    yield _format_sse_event(
        "status",
        {"status": "started", "message": "Processing your request..."},
    )

    accumulated_text = ""
    total_tokens = 0
    total_cost = 0.0
    used_provider = provider or "unknown"
    used_model = model or "unknown"
    used_department = "general"
    used_department_reason = ""
    start_time = time.time()
    response_message_id = str(uuid.uuid4())

    try:
        try:
            conversation = await _cr._require_owned_conversation(conversation_id, current_user)
        except HTTPException:
            error_event = {
                "type": "error",
                "code": "auth-failed",
                "message": "You do not have permission to access this conversation.",
                "is_recoverable": False,
                "done": True,
            }
            yield _format_sse_event("error", error_event)
            return

        sanitized_message, _ = _cr.InputSanitizer.sanitize_chat_message(message)

        # Intent + department routing via shared pipeline (avoids duplicating classification logic)
        _stream_intent_meta = {}
        try:
            from .messages import _get_request_pipeline  # noqa: PLC0415

            _dec, _exec = await _get_request_pipeline().run_routing_only(
                sanitized_message=sanitized_message,
                preferred_provider=provider,
                preferred_model=model,
            )
            if _dec.intent is not None:
                _stream_intent_meta = _dec.intent.to_dict()
            used_department = _exec.selected_department or "general"
            used_department_reason = _exec.department_selection_reason
            if not provider and _exec.selected_provider:
                used_provider = _exec.selected_provider
                used_model = _exec.selected_model or "unknown"
        except Exception:
            pass

        # Persist the user turn before invoking the provider so failures
        # downstream still leave the message in conversation history.
        try:
            await _cr.conversation_store.add_message_to_conversation(
                conversation_id=conversation_id,
                role="user",
                content=sanitized_message,
                metadata={"intent": _stream_intent_meta} if _stream_intent_meta else {},
            )
            await schedule_conversation_archive(conversation_id)
        except Exception as db_exc:
            logger.error("db_write_error", exc=db_exc, stage="user_message_store")
            error_event = {
                "type": "error",
                "code": "db-write-error",
                "message": "Failed to save your message. Please retry.",
                "is_recoverable": True,
                "details": {"stage": "message_storage"},
                "done": True,
            }
            yield _format_sse_event("error", error_event)
            return

        try:
            conversation = await _cr._require_owned_conversation(conversation_id, current_user)
            messages = [{"role": msg.role, "content": msg.content} for msg in conversation.messages]
            payload = {
                "messages": messages,
                "model": model,
                "user_id": str(current_user.id),
            }
        except Exception as build_exc:
            logger.error("message_build_error", exc=build_exc)
            error_event = {
                "type": "error",
                "code": "message-build-error",
                "message": "Failed to build conversation context.",
                "is_recoverable": False,
                "done": True,
            }
            yield _format_sse_event("error", error_event)
            return

        try:
            provider_response = await _cr.invoke_provider(
                pid=used_provider if provider is None else provider,
                model=used_model if model is None else model,
                payload=payload,
                timeout_ms=30000,
                stream=True,
            )
        except asyncio.TimeoutError:
            logger.warning("provider_timeout", provider=used_provider, model=used_model)
            error_event = {
                "type": "error",
                "code": "provider-timeout",
                "message": "The service timed out. Your message was saved.",
                "is_recoverable": True,
                "details": {"department": used_department},
                "done": True,
            }
            yield _format_sse_event("error", error_event)
            return
        except Exception as provider_connect_exc:
            logger.error(
                "provider_connection_error", exc=provider_connect_exc, provider=used_provider
            )
            error_event = {
                "type": "error",
                "code": "provider-connection-error",
                "message": "Processing service is temporarily unavailable. Your message was saved.",
                "is_recoverable": True,
                "details": {"department": used_department},
                "done": True,
            }
            yield _format_sse_event("error", error_event)
            return

        if not isinstance(provider_response, dict) or not provider_response.get("ok"):
            provider_error = (
                provider_response.get("error", "unknown-error")
                if isinstance(provider_response, dict)
                else "provider-error"
            )
            logger.warning("provider_error", error=provider_error, provider=used_provider)

            try:
                fallback_response = await _cr.invoke_provider(
                    pid=used_provider,
                    model=used_model,
                    payload=payload,
                    timeout_ms=30000,
                    stream=False,
                )
                if isinstance(fallback_response, dict) and fallback_response.get("ok"):
                    result_data = fallback_response.get("result", {})
                    accumulated_text = result_data.get("text", str(fallback_response))
                    used_provider = fallback_response.get("provider", used_provider)
                    used_model = fallback_response.get("model", used_model)
                    yield _format_sse_event(
                        "chunk",
                        {
                            "content": accumulated_text,
                            "token_count": 0,
                            "cost_delta": 0,
                            "done": False,
                        },
                    )
                else:
                    fallback_error = (
                        fallback_response.get("error", "unknown")
                        if isinstance(fallback_response, dict)
                        else "unknown"
                    )
                    logger.error("provider_fallback_failed", error=fallback_error)
                    error_event = {
                        "type": "error",
                        "code": "provider-error",
                        "message": "Processing service could not complete your request. Your message was saved.",
                        "is_recoverable": True,
                        "details": {"department": used_department},
                        "done": True,
                    }
                    yield _format_sse_event("error", error_event)
                    return
            except asyncio.TimeoutError:
                logger.error("provider_fallback_timeout", provider=used_provider)
                error_event = {
                    "type": "error",
                    "code": "provider-timeout",
                    "message": "Processing timed out. Your message was saved.",
                    "is_recoverable": True,
                    "done": True,
                }
                yield _format_sse_event("error", error_event)
                return
            except Exception as fallback_exc:
                logger.error("provider_fallback_error", exc=fallback_exc)
                error_event = {
                    "type": "error",
                    "code": "provider-error",
                    "message": "Processing service unavailable. Your message was saved.",
                    "is_recoverable": True,
                    "done": True,
                }
                yield _format_sse_event("error", error_event)
                return

        elif provider_response.get("stream"):
            used_provider = provider_response.get("provider", used_provider)
            used_model = provider_response.get("model", used_model)
            try:
                stream_gen = provider_response["stream"]
                async for chunk in stream_gen:
                    try:
                        chunk_text = (
                            chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
                        )
                        if not chunk_text:
                            continue
                        accumulated_text += chunk_text
                        token_estimate = max(1, len(chunk_text) // 4)
                        total_tokens += token_estimate
                        yield _format_sse_event(
                            "chunk",
                            {
                                "content": chunk_text,
                                "token_count": token_estimate,
                                "cost_delta": 0,
                                "done": False,
                            },
                        )
                    except Exception as chunk_exc:
                        # Skip the bad chunk rather than aborting the whole stream.
                        logger.error("chunk_processing_error", exc=chunk_exc)
                        continue
            except asyncio.TimeoutError:
                logger.warning("stream_timeout", partial_response_len=len(accumulated_text))
                error_event = {
                    "type": "error",
                    "code": "stream-timeout",
                    "message": "Stream interrupted mid-response. Partial response received.",
                    "is_recoverable": True,
                    "details": {"partial_response": accumulated_text[:100]},
                    "done": True,
                }
                yield _format_sse_event("error", error_event)
                return
            except Exception as stream_exc:
                logger.error(
                    "streaming_error",
                    exc=stream_exc,
                    partial_response_len=len(accumulated_text),
                )
                if accumulated_text:
                    error_event = {
                        "type": "error",
                        "code": "stream-interrupted",
                        "message": "Response stream was interrupted. Partial response saved.",
                        "is_recoverable": True,
                        "details": {"has_partial_response": True},
                        "done": True,
                    }
                    yield _format_sse_event("error", error_event)
                else:
                    error_event = {
                        "type": "error",
                        "code": "stream-error",
                        "message": "Failed to stream response. Your message was saved.",
                        "is_recoverable": True,
                        "done": True,
                    }
                    yield _format_sse_event("error", error_event)
                return
        else:
            # Provider returned ok but no stream key — extract text directly.
            result_data = provider_response.get("result", {})
            accumulated_text = result_data.get("text", "")
            used_provider = provider_response.get("provider", used_provider)
            used_model = provider_response.get("model", used_model)
            if accumulated_text:
                yield _format_sse_event(
                    "chunk",
                    {
                        "content": accumulated_text,
                        "token_count": 0,
                        "cost_delta": 0,
                        "done": False,
                    },
                )

        try:
            await _cr.conversation_store.add_message_to_conversation(
                conversation_id=conversation_id,
                role="assistant",
                content=accumulated_text,
                metadata={"provider": used_provider, "model": used_model},
                message_id=response_message_id,
            )
            await event_emitter.emit(
                "chat.message.created",
                source="api.chat_router.streaming",
                actor_user_id=current_user.id,
                payload=ChatMessageCreatedPayload(
                    conversation_id=conversation_id,
                    message_id=response_message_id,
                    role="assistant",
                    provider=used_provider,
                    model=used_model,
                    has_attachments=False,
                ),
            )
            await schedule_conversation_archive(conversation_id)
        except Exception as db_response_exc:
            logger.error("db_write_error", exc=db_response_exc, stage="assistant_message_store")
            # Response was already streamed — warn rather than error.
            error_event = {
                "type": "warning",
                "code": "response-storage-failed",
                "message": "Unable to save assistant response to history, but response was generated.",
                "is_recoverable": False,
                "done": True,
            }
            yield _format_sse_event("warning", error_event)
            return

        try:
            task_store = await get_task_store()
            task_id = str(uuid.uuid4())
            await task_store.save_task(
                task_id,
                {
                    "task_id": task_id,
                    "user_id": current_user.id,
                    "status": "completed",
                    "task_type": "chat.completion.stream",
                    "payload": {
                        "task": sanitized_message,
                        "conversation_id": conversation_id,
                    },
                    "result": {
                        "selected_provider": used_provider,
                        "model": used_model,
                        "department": used_department,
                        "usage": {"total_tokens": int(total_tokens)},
                        "cost_usd": float(total_cost),
                        "result": {"text": accumulated_text},
                    },
                    "metadata": {
                        "source": "chat.generate_chat_stream",
                        "conversation_id": conversation_id,
                        "assistant_message_id": response_message_id,
                    },
                },
            )
        except Exception as task_err:  # noqa: BLE001
            logger.warning(
                "stream_chat_task_history_write_failed",
                conversation_id=conversation_id,
                message_id=response_message_id,
                error=str(task_err),
            )

        try:
            usage_store = await get_usage_event_store()
            await usage_store.save_event(
                {
                    "user_id": current_user.id,
                    "conversation_id": conversation_id,
                    "message_id": response_message_id,
                    "provider": used_provider,
                    "model": used_model,
                    "total_tokens": int(total_tokens),
                    "cost_usd": float(total_cost),
                    "metadata": {"source": "chat.generate_chat_stream"},
                }
            )
        except Exception as usage_err:  # noqa: BLE001
            logger.warning(
                "stream_usage_event_write_failed",
                conversation_id=conversation_id,
                message_id=response_message_id,
                error=str(usage_err),
            )

        duration_ms = int((time.time() - start_time) * 1000)

        yield _format_sse_event(
            "complete",
            {
                "result": accumulated_text,
                "cost": total_cost,
                "tokens": total_tokens,
                "department": used_department,
                "department_reason": used_department_reason,
                "duration_ms": duration_ms,
                "message_id": response_message_id,
                "done": True,
            },
        )

    except HTTPException as http_exc:
        logger.warning("http_exception", status=http_exc.status_code, detail=http_exc.detail)
        error_event = {
            "type": "error",
            "code": f"http-{http_exc.status_code}",
            "message": str(http_exc.detail),
            "is_recoverable": False,
            "done": True,
        }
        yield _format_sse_event("error", error_event)
    except Exception as exc:
        logger.exception("streaming_error_unhandled", exc=exc)
        error_event = {
            "type": "error",
            "code": "internal-error",
            "message": "An unexpected error occurred. Your message was saved if it got this far.",
            "is_recoverable": False,
            "done": True,
        }
        yield _format_sse_event("error", error_event)


@router.post("/stream")
async def stream_chat(
    request: StreamChatRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Stream chat response using Server-Sent Events."""
    try:
        return StreamingResponse(
            generate_chat_stream(
                message=request.message,
                conversation_id=request.conversation_id,
                current_user=current_user,
                provider=request.provider,
                model=request.model,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
            },
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Chat streaming failed")
