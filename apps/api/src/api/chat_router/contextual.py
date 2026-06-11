"""Contextual chat endpoint — RAG context assembly + token budgeting.

Also hosts the debug endpoint that surfaces context-assembly configuration
and the legacy OpenAI-compatible `chat_completion` (currently defined but
intentionally not routed — preserves original behavior).
"""

import uuid
from datetime import datetime
from typing import Any, Dict

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.config.archetypes import (
    is_deep_research_mode as _is_deep_research_mode,
)
from api.config.archetypes import (
    is_general_assistant_mode as _is_general_assistant_mode,
)
from api.config.archetypes import (
    missing_deep_research_tools as _missing_deep_research_tools,
)
from api.config.archetypes import (
    missing_general_assistant_tools as _missing_general_assistant_tools,
)
from api.config.mode_addendums import get_addendum as _get_mode_addendum
from api.config.system_prompt import EDUCATION_SYSTEM_ADDENDUM, system_prompt_manager

from ..assistant_tools.executor import extract_tool_calls_contract, run_tool_loop
from ..assistant_tools.registry import export_tools_for_provider
from ..auth.router import User as AuthenticatedUser
from ..auth.router import get_current_user
from ..core.contracts import SuccessEnvelope
from ..storage import conversation_store
from ..storage.database import get_readonly_db
from . import _runtime as _cr
from .archiving import schedule_conversation_archive
from .schemas import ContextualChatRequest, ContextualChatResponse
from .service_accessors import (
    _get_context_assembly_service,
    _get_message_classifier,
)


def _get_embedding_worker():
    from ..services.embedding_worker import embedding_worker

    return embedding_worker


logger = structlog.get_logger()

router = APIRouter()


@router.post("/contextual-chat", response_model=SuccessEnvelope[ContextualChatResponse])
async def contextual_chat(
    request: ContextualChatRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_readonly_db),
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
                conversation = await conversation_store.get_conversation(conversation_id)
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
                "assembly_time": assembly_result.get("assembly_log", {}).get("assembly_time"),
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

        payload = {
            "messages": messages,
            "model": request.model,
            "user_id": str(user_id),
        }

        ctx_tools = export_tools_for_provider(request.provider)
        if _is_general_assistant_mode(request.mode) and ctx_tools:
            missing_tools = _missing_general_assistant_tools(ctx_tools)
            if missing_tools:
                logger.warning(
                    "general_assistant_required_tools_missing",
                    provider=request.provider,
                    mode=request.mode,
                    missing_tools=missing_tools,
                    registered_tool_count=len(ctx_tools),
                )
        if _is_deep_research_mode(request.mode) and ctx_tools:
            missing_tools = _missing_deep_research_tools(ctx_tools)
            if missing_tools:
                logger.warning(
                    "deep_research_required_tools_missing",
                    provider=request.provider,
                    mode=request.mode,
                    missing_tools=missing_tools,
                    registered_tool_count=len(ctx_tools),
                )
        if ctx_tools:
            payload["tools"] = ctx_tools

        # Resolve department for contextual chat
        _ctx_dept = request.department or "general"
        _ctx_dept_provider = request.provider
        _ctx_dept_model = request.model
        if request.department and not request.provider:
            try:
                from api.departments import department_dispatcher as _dd  # noqa: PLC0415

                _ctx_dept_id = _dd.resolve_provider_id(request.department)
                if _ctx_dept_id:
                    _ctx_dept_provider = _ctx_dept_id
            except Exception:
                pass

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
                    provider=_ctx_dept_provider,
                    model=_ctx_dept_model,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        provider_response = await _cr.invoke_provider(
            pid=_ctx_dept_provider,
            model=_ctx_dept_model,
            payload=payload,
            timeout_ms=30000,
            stream=False,
        )
        if (
            ctx_tools
            and isinstance(provider_response, dict)
            and provider_response.get("ok")
            and extract_tool_calls_contract(provider_response)
        ):
            provider_response = await run_tool_loop(
                messages=list(messages),
                invoke_fn=_cr.invoke_provider,
                provider=_ctx_dept_provider,
                model=_ctx_dept_model,
                tools=ctx_tools,
                timeout_ms=30000,
                user_id=user_id,
                conversation_id=conversation_id,
            )

        if isinstance(provider_response, dict) and provider_response.get("ok"):
            result_data = provider_response.get("result", {})
            response_content = result_data.get("text", "")
            used_provider = provider_response.get("provider", request.provider or "unknown")
            used_model = provider_response.get("model", request.model or "unknown")
        elif isinstance(provider_response, dict) and "choices" in provider_response:
            response_content = provider_response["choices"][0]["message"]["content"]
            used_provider = provider_response.get("provider", request.provider or "unknown")
            used_model = provider_response.get("model", request.model or "unknown")
        else:
            if isinstance(provider_response, dict) and not provider_response.get("ok"):
                _cr._raise_structured_provider_error(provider_response)

            response_content = str(provider_response)
            used_provider = request.provider or "unknown"
            used_model = request.model or "unknown"

        response_message_id = str(uuid.uuid4())

        if conversation_id:
            await conversation_store.add_message_to_conversation(
                conversation_id=conversation_id,
                role="user",
                content=request.message,
                metadata=(
                    {
                        "context_assembly_enabled": request.enable_context_assembly,
                        "context_assembly_layers": (
                            len(context_assembly.get("layers", [])) if context_assembly else 0
                        ),
                        "metadata": request.metadata,
                    }
                    if request.enable_context_assembly
                    else request.metadata
                ),
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
            await schedule_conversation_archive(conversation_id)

            # Queue both messages for embedding so they're retrievable by RAG
            # on future turns. Fire-and-forget — never blocks the response.
            try:
                worker = _get_embedding_worker()
                user_msg_id = str(uuid.uuid4())
                await worker.queue_message_embedding(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    message_id=user_msg_id,
                    content=request.message,
                )
                await worker.queue_message_embedding(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    message_id=response_message_id,
                    content=response_content,
                    metadata={"provider": used_provider, "model": used_model},
                )
            except Exception as _emb_exc:
                logger.debug("embedding_queue_skipped", error=str(_emb_exc))

        visualizations = None
        if isinstance(provider_response, dict) and provider_response.get("visualizations"):
            visualizations = provider_response["visualizations"]

        return SuccessEnvelope(
            data=ContextualChatResponse(
                message_id=response_message_id,
                response=response_content,
                department=_ctx_dept,
                department_reason="",
                timestamp=datetime.utcnow().isoformat(),
                context_assembly=context_assembly,
                token_usage=token_usage,
                visualizations=visualizations,
            )
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "contextual_chat_failed",
            error=str(exc),
            error_type=type(exc).__name__,
        )
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
    except Exception as exc:
        logger.error(
            "debug_context_assembly_failed",
            error=str(exc),
            error_type=type(exc).__name__,
        )
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
