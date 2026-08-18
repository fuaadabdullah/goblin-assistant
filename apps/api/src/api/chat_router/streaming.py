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

from ..auth.router import User as AuthenticatedUser, get_current_user
from ..config.system_prompt import system_prompt_manager
from ..core.contracts import ChatMessageCreatedPayload
from ..observability.events import event_emitter
from . import _runtime as _cr
from .archiving import schedule_conversation_archive
from .helpers import _format_sse_event
from .messages.post_response import record_completion_artifacts
from .schemas import StreamChatRequest

_UNHANDLED_FALLBACK = "An unexpected error occurred. Your message was saved if it got this far."


def _format_unhandled_stream_error(exc: Exception) -> str:
    return str(exc) if str(exc) else _UNHANDLED_FALLBACK

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
    used_fallback = False
    ttft_ms: Optional[float] = None
    start_time = time.perf_counter()
    response_message_id = str(uuid.uuid4())

    try:
        try:
            conversation = await _cr._require_owned_conversation(
                conversation_id, current_user
            )
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

        # Persist the user turn before invoking the provider so failures
        # downstream still leave the message in conversation history.
        try:
            await _cr.conversation_store.add_message_to_conversation(
                conversation_id=conversation_id,
                role="user",
                content=sanitized_message,
            )
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
            conversation = await _cr._require_owned_conversation(
                conversation_id, current_user
            )
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in conversation.messages
            ]
            system_content = system_prompt_manager.compose()
            messages = [{"role": "system", "content": system_content}] + history
            payload = {"messages": messages, "model": model}
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
                pid=provider,
                model=model,
                payload=payload,
                timeout_ms=30000,
                stream=True,
            )
            if isinstance(provider_response, dict):
                ttft_value = provider_response.get("latency_ms")
                if isinstance(ttft_value, (int, float)):
                    ttft_ms = float(ttft_value)
        except asyncio.TimeoutError:
            logger.warning("provider_timeout", provider=provider, model=model)
            error_event = {
                "type": "error",
                "code": "provider-timeout",
                "message": f"Provider {provider or 'default'} did not respond in time. Your message was saved.",
                "is_recoverable": True,
                "details": {"provider": provider, "timeout_ms": 30000},
                "done": True,
            }
            yield _format_sse_event("error", error_event)
            return
        except Exception as provider_connect_exc:
            logger.error(
                "provider_connection_error", exc=provider_connect_exc, provider=provider
            )
            error_event = {
                "type": "error",
                "code": "provider-connection-error",
                "message": f"Could not reach provider {provider or 'default'}. Your message was saved.",
                "is_recoverable": True,
                "details": {"provider": provider},
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
            logger.warning("provider_error", error=provider_error, provider=provider)

            try:
                fallback_response = await _cr.invoke_provider(
                    pid=provider,
                    model=model,
                    payload=payload,
                    timeout_ms=30000,
                    stream=False,
                )
                if isinstance(fallback_response, dict) and fallback_response.get("ok"):
                    result_data = fallback_response.get("result", {})
                    accumulated_text = result_data.get("text", str(fallback_response))
                    used_provider = fallback_response.get("provider", used_provider)
                    used_model = fallback_response.get("model", used_model)
                    used_fallback = True
                    fallback_ttft = fallback_response.get("latency_ms")
                    if isinstance(fallback_ttft, (int, float)):
                        ttft_ms = float(fallback_ttft)
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
                        "message": f"Provider could not process your request: {provider_error}. Your message was saved.",
                        "is_recoverable": True,
                        "details": {"provider_error": provider_error},
                        "done": True,
                    }
                    yield _format_sse_event("error", error_event)
                    return
            except asyncio.TimeoutError:
                logger.error("provider_fallback_timeout", provider=provider)
                error_event = {
                    "type": "error",
                    "code": "provider-timeout",
                    "message": "Provider fallback timed out. Your message was saved.",
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
                    "message": "Provider unavailable. Your message was saved.",
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
                            chunk.get("text", "")
                            if isinstance(chunk, dict)
                            else str(chunk)
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
                logger.warning(
                    "stream_timeout", partial_response_len=len(accumulated_text)
                )
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
                "chat_router.streaming",
                payload=ChatMessageCreatedPayload(
                    conversation_id=conversation_id,
                    message_id=response_message_id,
                    role="assistant",
                    provider=used_provider,
                    model=used_model,
                ),
            )
            await schedule_conversation_archive(conversation_id)
        except Exception as db_response_exc:
            logger.error(
                "db_write_error", exc=db_response_exc, stage="assistant_message_store"
            )
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
            await record_completion_artifacts(
                current_user=current_user,
                conversation_id=conversation_id,
                user_message_id=None,
                response_message_id=response_message_id,
                sanitized_message=sanitized_message,
                response_content=accumulated_text,
                used_provider=used_provider,
                used_model=used_model,
                usage={"total_tokens": total_tokens} if total_tokens else None,
                cost_usd=None,
                correlation_id=None,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
                used_fallback=used_fallback,
                ttft_ms=ttft_ms,
                retrieval_latency_ms=None,
            )
        except Exception as record_exc:
            logger.warning("stream_completion_artifacts_failed", error=str(record_exc))

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        yield _format_sse_event(
            "complete",
            {
                "result": accumulated_text,
                "cost": total_cost,
                "tokens": total_tokens,
                "model": used_model,
                "provider": used_provider,
                "duration_ms": duration_ms,
                "message_id": response_message_id,
                "done": True,
            },
        )

    except HTTPException as http_exc:
        logger.warning(
            "http_exception", status=http_exc.status_code, detail=http_exc.detail
        )
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
            "message": _format_unhandled_stream_error(exc),
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
