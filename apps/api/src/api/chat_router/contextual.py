"""Contextual chat endpoint — RAG context assembly + token budgeting.

Also hosts the debug endpoint that surfaces context-assembly configuration
and the legacy OpenAI-compatible `chat_completion` (currently defined but
intentionally not routed — preserves original behavior).
"""

import time
import uuid
from datetime import datetime
from typing import Any, Dict

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..assistant_tools.executor import extract_tool_calls, run_tool_loop
from ..assistant_tools.registry import export_openai_tools
from ..auth.router import User as AuthenticatedUser, get_current_user
from ..storage import conversation_store
from ..storage.database import get_db
from api.config.mode_addendums import get_addendum as _get_mode_addendum
from api.config.system_prompt import EDUCATION_SYSTEM_ADDENDUM, system_prompt_manager
from . import _runtime as _cr
from .schemas import ContextualChatRequest, ContextualChatResponse
from .service_accessors import (
    _get_context_assembly_service,
    _get_message_classifier,
)

logger = structlog.get_logger()

router = APIRouter()


@router.post("/contextual-chat", response_model=ContextualChatResponse)
async def contextual_chat(
    request: ContextualChatRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Chat with the new fixed-order retrieval stack + strict token budgeting.

    Differs from /messages by NOT requiring a conversation_id upfront and by
    returning context-assembly diagnostics alongside the assistant reply.
    """
    try:
        user_id = current_user.id
        conversation_id = request.conversation_id

        if conversation_id:
            await _cr._assert_conversation_owned(conversation_id, current_user, db)

        if request.mode:
            try:
                addendum = _get_mode_addendum(request.mode)
            except KeyError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
        else:
            message_classifier, MessageType = _get_message_classifier()
            msg_classification = message_classifier.classify_message(request.message, "user")
            addendum = (
                EDUCATION_SYSTEM_ADDENDUM
                if msg_classification.message_type == MessageType.LEARNING
                else ""
            )

        context_assembly = None
        if request.enable_context_assembly and user_id:
            conversation_history = []
            if conversation_id:
                conversation = await conversation_store.get_conversation(
                    conversation_id
                )
                if conversation:
                    conversation_history = [
                        {"role": msg.role, "content": msg.content}
                        for msg in conversation.messages[-10:]
                    ]

            context_assembly_service = _get_context_assembly_service()
            assembly_result = await context_assembly_service.assemble_context(
                query=request.message,
                user_id=user_id,
                conversation_id=conversation_id,
                conversation_history=conversation_history,
                model=request.model,
            )

            context_assembly = assembly_result
            context_text = assembly_result.get("context", "")

            system_prompt = system_prompt_manager.get_complete_prompt_with_addendum(
                context=context_text,
                user_query=request.message,
                addendum=addendum,
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.message},
            ]

            token_usage = {
                "total_tokens_used": assembly_result.get("total_tokens_used", 0),
                "remaining_tokens": assembly_result.get("remaining_tokens", 0),
                "layers_assembled": len(assembly_result.get("layers", [])),
                "assembly_time": assembly_result.get("assembly_log", {}).get(
                    "assembly_time"
                ),
                "degraded_mode": assembly_result.get("degraded_mode", False),
                "degraded_reason": assembly_result.get("degraded_reason"),
                "truncation_warnings": assembly_result.get("truncation_warnings", []),
                "summary_fallback_applied": assembly_result.get("summary_fallback_applied", False),
            }

        else:
            system_prompt = system_prompt_manager.get_complete_prompt_with_addendum(
                user_query=request.message, addendum=addendum
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.message},
            ]
            token_usage = {"method": "fallback"}

        start_time = time.time()
        payload = {
            "messages": messages,
            "model": request.model,
        }

        ctx_tools = export_openai_tools()
        if ctx_tools:
            payload["tools"] = ctx_tools

        if request.stream:
            # Streaming requires a conversation; create one on the fly if missing.
            from .streaming import generate_chat_stream

            stream_conv_id = conversation_id
            if not stream_conv_id:
                new_conv = await conversation_store.create_conversation(
                    user_id=user_id, title=request.message[:50]
                )
                stream_conv_id = new_conv.conversation_id
            return StreamingResponse(
                generate_chat_stream(
                    message=request.message,
                    conversation_id=stream_conv_id,
                    current_user=current_user,
                    provider=request.provider,
                    model=request.model,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        try:
            provider_response = await _cr.invoke_provider(
                pid=request.provider,
                model=request.model,
                payload=payload,
                timeout_ms=30000,
                stream=False,
            )

            if (
                isinstance(provider_response, dict)
                and provider_response.get("ok")
                and extract_tool_calls(provider_response)
            ):
                provider_response = await run_tool_loop(
                    messages=list(messages),
                    invoke_fn=_cr.invoke_provider,
                    provider=request.provider,
                    model=request.model,
                    tools=ctx_tools if ctx_tools else None,
                    timeout_ms=30000,
                    user_id=user_id,
                    conversation_id=conversation_id,
                )

            duration = time.time() - start_time
            success = isinstance(provider_response, dict) and provider_response.get(
                "ok", True
            )
            error = None if success else str(provider_response.get("error", "unknown"))
        except Exception:
            duration = time.time() - start_time
            raise

        if isinstance(provider_response, dict) and provider_response.get("ok"):
            result_data = provider_response.get("result", {})
            response_content = result_data.get("text", "")
            used_provider = provider_response.get(
                "provider", request.provider or "unknown"
            )
            used_model = provider_response.get("model", request.model or "unknown")
        elif isinstance(provider_response, dict) and "choices" in provider_response:
            response_content = provider_response["choices"][0]["message"]["content"]
            used_provider = provider_response.get(
                "provider", request.provider or "unknown"
            )
            used_model = provider_response.get("model", request.model or "unknown")
        else:
            if isinstance(provider_response, dict) and not provider_response.get("ok"):
                error_msg = provider_response.get("error", "unknown-error")
                raise HTTPException(
                    status_code=500, detail=f"AI Provider error: {error_msg}"
                )

            response_content = str(provider_response)
            used_provider = request.provider or "unknown"
            used_model = request.model or "unknown"

        message_id = str(uuid.uuid4())
        response_message_id = str(uuid.uuid4())

        if conversation_id:
            await conversation_store.add_message_to_conversation(
                conversation_id=conversation_id,
                role="user",
                content=request.message,
                metadata={
                    "context_assembly_enabled": request.enable_context_assembly,
                    "context_assembly_layers": len(context_assembly.get("layers", []))
                    if context_assembly
                    else 0,
                    "metadata": request.metadata,
                }
                if request.enable_context_assembly
                else request.metadata,
            )

            await conversation_store.add_message_to_conversation(
                conversation_id=conversation_id,
                role="assistant",
                content=response_content,
                metadata={
                    "provider": used_provider,
                    "model": used_model,
                    "context_assembly_used": request.enable_context_assembly,
                    "token_usage": token_usage,
                },
            )

        visualizations = None
        if isinstance(provider_response, dict) and provider_response.get("visualizations"):
            visualizations = provider_response["visualizations"]

        return ContextualChatResponse(
            message_id=response_message_id,
            response=response_content,
            provider=used_provider,
            model=used_model,
            timestamp=datetime.utcnow().isoformat(),
            context_assembly=context_assembly,
            token_usage=token_usage,
            visualizations=visualizations,
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Contextual chat failed")


@router.get("/debug/context-assembly")
async def debug_context_assembly():
    """Debug endpoint to inspect context assembly configuration."""
    try:
        context_assembly_service = _get_context_assembly_service()
        debug_info = {
            "context_assembly": context_assembly_service.get_debug_info(),
            "system_prompt": system_prompt_manager.get_debug_info(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        return debug_info
    except Exception:
        raise HTTPException(status_code=500, detail="Debug endpoint failed")


# Legacy OpenAI-compatible completion handler.
#
# Preserves original behavior from the monolithic chat_router.py: defined but
# intentionally not registered as a route (no @router decorator). Kept so
# `api.chat_router.chat_completion` remains importable.
async def chat_completion(request: Dict[str, Any]):
    """OpenAI-compatible chat completions handler (not wired to a route).

    Mirrors the OpenAI Chat Completions request/response shape and passes
    straight through to the provider dispatcher without conversation storage.
    """
    try:
        messages = request.get("messages", [])
        model = request.get("model")
        stream = request.get("stream", False)

        payload = {
            "messages": messages,
            "model": model,
        }
        response = await _cr.invoke_provider(
            pid=None,
            model=model,
            payload=payload,
            timeout_ms=30000,
            stream=stream,
        )

        if isinstance(response, dict) and response.get("ok"):
            result_data = response.get("result", {})
            if "raw" in result_data:
                raw_response = result_data["raw"]
                if isinstance(raw_response, dict):
                    raw_response["provider"] = response.get("provider", "unknown")
                    raw_response["model"] = response.get("model", model or "unknown")
                return raw_response

        return response

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Chat completion failed")
