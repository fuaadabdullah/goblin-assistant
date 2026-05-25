"""POST /chat/conversations/{id}/messages — the primary send-message route.

Pipeline: validate ownership -> sanitize -> Write-Time Intelligence ->
optional RAG context assembly -> provider dispatch (with optional tool-calling
loop) -> normalize -> persist -> respond.

For streaming requests we delegate to streaming.generate_chat_stream.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..assistant_tools.executor import extract_tool_calls, run_tool_loop
from ..assistant_tools.registry import export_openai_tools
from ..auth.router import User as AuthenticatedUser, get_current_user
from ..providers.dispatcher import dispatcher
from api.config.mode_addendums import get_addendum as _get_mode_addendum
from api.config.system_prompt import EDUCATION_SYSTEM_ADDENDUM, system_prompt_manager
from . import _runtime as _cr
from .archiving import schedule_conversation_archive
from .schemas import (
    EstimateTokensResponse,
    LayerEstimate,
    SendMessageRequest,
    SendMessageResponse,
)
from .service_accessors import (
    _get_context_assembly_service,
    _get_message_classifier,
    _get_write_time_intelligence,
)
from .uploads import _pending_uploads

OUTPUT_TOKEN_RATIO = 0.4

logger = structlog.get_logger()

router = APIRouter()


@router.post(
    "/conversations/{conversation_id}/messages", response_model=SendMessageResponse
)
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Send a message and receive an AI response.

    On stream=True, returns SSE via streaming.generate_chat_stream. Provider
    selection is delegated to the dispatcher; tool-calling is run inline.
    """
    try:
        conversation = await _cr._require_owned_conversation(conversation_id, current_user)

        sanitized_message, message_validation = _cr.InputSanitizer.sanitize_chat_message(
            request.message
        )

        # Write-Time Intelligence: classify + plan actions for the inbound message.
        # Failures here must not block chat — fall through with error metadata.
        message_id = str(uuid.uuid4())
        message_metadata: Dict[str, Any] = {
            "input_validation": message_validation,
        }
        try:
            write_time_intelligence = _get_write_time_intelligence()
            write_time_result = await write_time_intelligence.process_message(
                message_id=message_id,
                content=sanitized_message,
                role="user",
                user_id=conversation.user_id,
                conversation_id=conversation_id,
                metadata=request.metadata,
            )

            classification = write_time_result["classification"]
            decision = write_time_result["decision"]
            execution = write_time_result["execution"]

            message_metadata.update({
                "classification": classification,
                "decision": decision,
                "write_time_execution": execution,
                "memory_type": classification["type"],
                "confidence": classification["confidence"],
                "actions_taken": execution["actions_executed"],
                "processed_at": write_time_result["processed_at"],
            })
        except Exception as wti_err:
            logger.error(
                "write_time_intelligence_failed",
                message_id=message_id,
                conversation_id=conversation_id,
                user_id=current_user.id,
                error_type=type(wti_err).__name__,
                error=str(wti_err),
            )
            message_metadata["write_time_error"] = str(wti_err)

        if request.metadata:
            message_metadata.update(request.metadata)

        # Drain any pending uploads referenced by the request into the message metadata.
        if request.attachment_ids:
            attachments_meta = []
            for aid in request.attachment_ids:
                upload = _pending_uploads.pop(aid, None)
                if upload and upload["user_id"] == current_user.id:
                    attachments_meta.append(
                        {
                            "id": upload["file_id"],
                            "filename": upload["filename"],
                            "mime_type": upload["mime_type"],
                            "size_bytes": upload["size_bytes"],
                        }
                    )
            if attachments_meta:
                message_metadata["attachments"] = attachments_meta

        user_msg_saved = await _cr.conversation_store.add_message_to_conversation(
            conversation_id=conversation_id,
            role="user",
            content=sanitized_message,
            metadata=message_metadata,
            message_id=message_id,
        )
        if not user_msg_saved:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found when saving user message",
            )
        await schedule_conversation_archive(conversation_id)

        # Reload to include the just-saved user message in the provider payload.
        conversation = await _cr._require_owned_conversation(conversation_id, current_user)
        history_messages = [
            {"role": msg.role, "content": msg.content} for msg in conversation.messages
        ]

        if request.mode:
            try:
                addendum = _get_mode_addendum(request.mode)
            except KeyError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
        else:
            message_classifier, MessageType = _get_message_classifier()
            msg_classification = message_classifier.classify_message(sanitized_message, "user")
            addendum = (
                EDUCATION_SYSTEM_ADDENDUM
                if msg_classification.message_type == MessageType.LEARNING
                else ""
            )

        context_metadata: Dict[str, Any] = {}
        if request.enable_context_assembly:
            try:
                context_assembly_service = _get_context_assembly_service()
                assembly_result = await context_assembly_service.assemble_context(
                    query=sanitized_message,
                    user_id=current_user.id,
                    conversation_id=conversation_id,
                    conversation_history=history_messages[-10:],
                    model=request.model,
                )
                context_text = assembly_result.get("context", "")
                system_prompt = system_prompt_manager.get_complete_prompt_with_addendum(
                    context=context_text,
                    user_query=sanitized_message,
                    addendum=addendum,
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                ] + history_messages
                context_metadata = {
                    "context_assembly_enabled": True,
                    "context_assembly_layers": len(assembly_result.get("layers", [])),
                    "total_tokens_used": assembly_result.get("total_tokens_used", 0),
                    "degraded_mode": assembly_result.get("degraded_mode", False),
                    "degraded_reason": assembly_result.get("degraded_reason"),
                    "truncation_warnings": assembly_result.get("truncation_warnings", []),
                    "summary_fallback_applied": assembly_result.get("summary_fallback_applied", False),
                }
            except Exception as ctx_err:
                logger.warning(
                    "context_assembly_failed_in_send_message",
                    conversation_id=conversation_id,
                    error=str(ctx_err),
                )
                messages = history_messages
                context_metadata = {
                    "context_assembly_enabled": False,
                    "context_assembly_error": str(ctx_err),
                }
        else:
            messages = history_messages

        payload = {
            "messages": messages,
            "model": request.model,
        }

        registered_tools = export_openai_tools()
        if registered_tools:
            payload["tools"] = registered_tools

        if request.stream:
            from .streaming import generate_chat_stream

            return StreamingResponse(
                generate_chat_stream(
                    message=request.message,
                    conversation_id=conversation_id,
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

        provider_response = await _cr.invoke_provider(
            pid=request.provider,
            model=request.model,
            payload=payload,
            timeout_ms=30000,
            stream=False,
        )

        # If the model returned tool_calls, run them and re-invoke until we get text.
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
                tools=registered_tools if registered_tools else None,
                timeout_ms=30000,
                user_id=current_user.id,
                conversation_id=conversation_id,
            )

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
                _cr._raise_structured_provider_error(provider_response)

            response_content = str(provider_response)
            used_provider = request.provider or "unknown"
            used_model = request.model or "unknown"

        usage, cost_usd, correlation_id = _cr._extract_usage_and_cost(provider_response)

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
            await schedule_conversation_archive(conversation_id)

        visualizations = None
        if isinstance(provider_response, dict) and provider_response.get("visualizations"):
            visualizations = provider_response["visualizations"]

        return SendMessageResponse(
            message_id=response_message_id,
            response=response_content,
            provider=used_provider,
            model=used_model,
            timestamp=datetime.utcnow().isoformat(),
            usage=usage,
            cost_usd=cost_usd,
            correlation_id=correlation_id,
            visualizations=visualizations,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "send_message_unhandled_error",
            error=str(e),
            error_type=type(e).__name__,
            conversation_id=conversation_id,
            user_id=current_user.id,
        )
        raise HTTPException(status_code=500, detail="Failed to send message")


def _resolve_provider_id(requested: Optional[str]) -> Optional[str]:
    """Mirror dispatcher provider selection so the estimate matches the real send."""
    candidates = dispatcher._candidate_order(requested)
    return candidates[0] if candidates else None


@router.post("/estimate-tokens", response_model=EstimateTokensResponse)
async def estimate_tokens(
    request: SendMessageRequest,
    conversation_id: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> EstimateTokensResponse:
    """Estimate token usage and cost for a message without invoking the provider.

    Runs the same context-assembly pipeline as send_message so the estimate
    reflects what the real call would consume. Output tokens are a fixed
    OUTPUT_TOKEN_RATIO heuristic; this is a UI hint, not a guarantee.
    """
    history_messages: list[dict] = []
    if conversation_id:
        conversation = await _cr._require_owned_conversation(
            conversation_id, current_user
        )
        history_messages = [
            {"role": m.role, "content": m.content} for m in conversation.messages
        ]

    layers: list[LayerEstimate] = []
    input_tokens = 0
    degraded_mode = False
    degraded_reason: Optional[str] = None

    if request.enable_context_assembly:
        try:
            assembly = await _get_context_assembly_service().assemble_context(
                query=request.message,
                user_id=current_user.id,
                conversation_id=conversation_id,
                conversation_history=history_messages[-10:],
            )
            input_tokens = int(assembly.get("total_tokens_used") or 0)
            for layer in assembly.get("layers", []):
                name = getattr(layer, "name", None) or (
                    layer.get("name") if isinstance(layer, dict) else "?"
                )
                tokens = getattr(layer, "tokens", None) or (
                    layer.get("tokens", 0) if isinstance(layer, dict) else 0
                )
                layers.append(LayerEstimate(name=str(name), tokens=int(tokens)))
            if not input_tokens:
                input_tokens = sum(l.tokens for l in layers)
            degraded_mode = bool(assembly.get("degraded_mode", False))
            degraded_reason = assembly.get("degraded_reason")
        except Exception as ctx_err:
            logger.warning(
                "context_assembly_failed_in_estimate_tokens",
                conversation_id=conversation_id,
                error=str(ctx_err),
            )
            degraded_mode = True
            degraded_reason = str(ctx_err)

    estimated_output_tokens = int(input_tokens * OUTPUT_TOKEN_RATIO)

    provider_id = _resolve_provider_id(request.provider)
    if provider_id is None:
        return EstimateTokensResponse(
            input_tokens=input_tokens,
            estimated_output_tokens=estimated_output_tokens,
            estimated_cost_usd=0.0,
            provider="unknown",
            model=request.model,
            layers=layers,
            degraded_mode=True,
            degraded_reason=degraded_reason or "no-configured-providers",
        )

    provider = dispatcher.get_provider(provider_id)
    estimated_cost_usd = provider.estimate_cost(
        input_tokens, estimated_output_tokens
    )

    return EstimateTokensResponse(
        input_tokens=input_tokens,
        estimated_output_tokens=estimated_output_tokens,
        estimated_cost_usd=estimated_cost_usd,
        provider=provider_id,
        model=request.model,
        layers=layers,
        degraded_mode=degraded_mode,
        degraded_reason=degraded_reason,
    )
