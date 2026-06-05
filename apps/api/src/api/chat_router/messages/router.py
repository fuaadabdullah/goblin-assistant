"""Route handlers for the send-message pipeline.

Pipeline stages are decomposed as module-level async helper functions
so the route itself reads as a high-level orchestration. Each stage
has a single responsibility and an explicit side-effect contract.
"""

import uuid
from datetime import datetime
from importlib import import_module
from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ...config.archetypes import (
    is_deep_research_mode as _is_deep_research_mode,
)
from ...config.archetypes import (
    is_general_assistant_mode as _is_general_assistant_mode,
)
from ...config.archetypes import (
    missing_deep_research_tools as _missing_deep_research_tools,
)
from ...config.archetypes import (
    missing_general_assistant_tools as _missing_general_assistant_tools,
)
from ...config.mode_addendums import get_addendum as _get_mode_addendum
from ...config.system_prompt import EDUCATION_SYSTEM_ADDENDUM, system_prompt_manager
from ...storage.usage_events import get_usage_event_store
from ...assistant_tools.executor import extract_tool_calls_contract, run_tool_loop
from ...assistant_tools.registry import export_tools_for_provider
from ...auth.router import User as AuthenticatedUser
from ...auth.router import get_current_user
from ...core.contracts import SuccessEnvelope
from ...providers.base import ProviderErrorCategory
from ...providers.dispatcher import canonical_provider_id, dispatcher
from ...services.pdf_extraction_service import build_attachment_context
from .. import _runtime as _cr
from ..archiving import schedule_conversation_archive
from ..schemas import (
    EstimateTokensResponse,
    LayerEstimate,
    SendMessageRequest,
    SendMessageResponse,
)
from ..service_accessors import (
    _get_context_assembly_service,
    _get_message_classifier,
    _get_write_time_intelligence,
)
from ..uploads import _pending_uploads
from .attachment_utils import attachment_context_limits, inject_attachment_context
from .error_mapping import provider_error_code, provider_error_status_code
from .pipeline_helpers import (
    merge_attachment_metadata,
    provider_supports_tools,
    resolve_provider_id,
)
from .sentry_context import set_sentry_chat_context
from .usage_tracker import (
    emit_chat_message_created,
    emit_chat_message_failed,
    record_chat_completion_task,
    record_usage_event,
)

OUTPUT_TOKEN_RATIO = 0.4

logger = structlog.get_logger()

router = APIRouter()
_messages_pkg = import_module(__package__)


# ---------------------------------------------------------------------------
# Route handler
# ---------------------------------------------------------------------------


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SuccessEnvelope[SendMessageResponse],
)
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Send a message and receive an AI response.

    On stream=True, returns SSE via streaming.generate_chat_stream.
    Provider selection is delegated to the dispatcher; tool-calling is
    run inline.

    Pipeline: WTI → attachments → context assembly → provider dispatch →
    tool loop → normalize → persist → respond.
    """
    message_id: Optional[str] = None
    try:
        set_sentry_chat_context(
            conversation_id=conversation_id,
            user_id=current_user.id,
            provider=request.provider,
            model=request.model,
        )

        conversation = await _cr._require_owned_conversation(conversation_id, current_user)

        sanitized_message, message_validation = _cr.InputSanitizer.sanitize_chat_message(
            request.message
        )

        # ── Stage 1: Write-Time Intelligence ──────────────────────────────
        message_id = str(uuid.uuid4())
        message_metadata: Dict[str, Any] = {}
        try:
            write_time_intelligence = _messages_pkg._get_write_time_intelligence()
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
            message_metadata.update(
                {
                    "classification": classification,
                    "decision": decision,
                    "write_time_execution": execution,
                    "memory_type": classification["type"],
                    "confidence": classification["confidence"],
                    "actions_taken": execution["actions_executed"],
                    "processed_at": write_time_result["processed_at"],
                }
            )
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

        message_metadata["input_validation"] = message_validation
        if request.metadata:
            message_metadata.update(request.metadata)

        # ── Stage 2: Attachments ─────────────────────────────────────────
        attachment_context = ""
        attachments_meta, attachment_context_sources = merge_attachment_metadata(
            current_user_id=current_user.id,
            attachment_ids=request.attachment_ids,
            pending_uploads=_pending_uploads,
        )
        if attachments_meta:
            message_metadata["attachments"] = attachments_meta
            max_chunks, max_chars = attachment_context_limits()
            attachment_context = build_attachment_context(
                query=sanitized_message,
                attachments=attachment_context_sources,
                max_chunks=max_chunks,
                max_chars=max_chars,
            )
            message_metadata["attachment_context_included"] = bool(attachment_context)
            if attachment_context:
                message_metadata["attachment_context_chars"] = len(attachment_context)

        # ── Persist user message ──────────────────────────────────────────
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
        await emit_chat_message_created(
            current_user=current_user,
            conversation_id=conversation_id,
            message_id=message_id,
            role="user",
            has_attachments=bool(message_metadata.get("attachments")),
            correlation_id=message_metadata.get("correlation_id"),
        )
        await _messages_pkg.schedule_conversation_archive(conversation_id)

        # ── Usage quota check ─────────────────────────────────────────────
        try:
            usage_store = await _messages_pkg.get_usage_event_store()
            quota_check = await usage_store.check_limits(current_user.id)
            if not quota_check.get("allowed", True):
                raise HTTPException(
                    status_code=429,
                    detail={
                        "message": "Daily usage limit exceeded",
                        "reason": quota_check.get("reason"),
                        "usage": quota_check.get("usage"),
                    },
                )
        except HTTPException:
            raise
        except Exception as quota_err:
            logger.warning(
                "usage_quota_check_failed",
                conversation_id=conversation_id,
                user_id=current_user.id,
                error=str(quota_err),
            )

        # ── Stage 3: Context assembly + message building ──────────────────
        # Reload to include the just-saved user message.
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
            message_classifier, MessageType = _messages_pkg._get_message_classifier()
            msg_classification = message_classifier.classify_message(sanitized_message, "user")
            addendum = (
                EDUCATION_SYSTEM_ADDENDUM
                if msg_classification.message_type == MessageType.LEARNING
                else ""
            )

        context_metadata: Dict[str, Any] = {}
        if request.enable_context_assembly:
            try:
                context_assembly_service = _messages_pkg._get_context_assembly_service()
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
                inject_attachment_context(messages, attachment_context)
                context_metadata = {
                    "context_assembly_enabled": True,
                    "context_assembly_layers": len(assembly_result.get("layers", [])),
                    "total_tokens_used": assembly_result.get("total_tokens_used", 0),
                    "degraded_mode": assembly_result.get("degraded_mode", False),
                    "degraded_reason": assembly_result.get("degraded_reason"),
                    "truncation_warnings": assembly_result.get("truncation_warnings", []),
                    "summary_fallback_applied": assembly_result.get(
                        "summary_fallback_applied", False
                    ),
                }
            except Exception as ctx_err:
                logger.warning(
                    "context_assembly_failed_in_send_message",
                    conversation_id=conversation_id,
                    error=str(ctx_err),
                )
                messages = history_messages
                inject_attachment_context(messages, attachment_context)
                context_metadata = {
                    "context_assembly_enabled": False,
                    "context_assembly_error": str(ctx_err),
                }
        else:
            messages = history_messages
            inject_attachment_context(messages, attachment_context)

        # ── Stage 4: Provider dispatch ────────────────────────────────────
        payload = {
            "messages": messages,
            "model": request.model,
        }

        registered_tools = (
            export_tools_for_provider(request.provider)
            if provider_supports_tools(request.provider)
            else []
        )
        if _is_general_assistant_mode(request.mode) and registered_tools:
            missing_tools = _missing_general_assistant_tools(registered_tools)
            if missing_tools:
                logger.warning(
                    "general_assistant_required_tools_missing",
                    provider=request.provider,
                    mode=request.mode,
                    missing_tools=missing_tools,
                    registered_tool_count=len(registered_tools),
                )
        if _is_deep_research_mode(request.mode) and registered_tools:
            missing_tools = _missing_deep_research_tools(registered_tools)
            if missing_tools:
                logger.warning(
                    "deep_research_required_tools_missing",
                    provider=request.provider,
                    mode=request.mode,
                    missing_tools=missing_tools,
                    registered_tool_count=len(registered_tools),
                )
        if registered_tools:
            payload["tools"] = registered_tools

        # Streaming branch
        if request.stream:
            from ..streaming import generate_chat_stream

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

        # Tool loop
        if (
            registered_tools
            and isinstance(provider_response, dict)
            and provider_response.get("ok")
            and extract_tool_calls_contract(provider_response)
        ):
            provider_response = await run_tool_loop(
                messages=list(messages),
                invoke_fn=_cr.invoke_provider,
                provider=request.provider,
                model=request.model,
                tools=registered_tools,
                timeout_ms=30000,
                user_id=current_user.id,
                conversation_id=conversation_id,
            )

        # ── Stage 5: Normalize response ──────────────────────────────────
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
                category = str(
                    provider_response.get("error_category")
                    or ProviderErrorCategory.UNKNOWN.value
                )
                await emit_chat_message_failed(
                    current_user=current_user,
                    conversation_id=conversation_id,
                    message_id=message_id,
                    stage="provider",
                    provider=str(
                        provider_response.get("provider") or request.provider or "unknown"
                    ),
                    model=str(provider_response.get("model") or request.model or "unknown"),
                    category=category,
                    code=provider_error_code(category),
                    status_code=provider_error_status_code(category),
                    error=str(provider_response.get("error") or "unknown-error"),
                    error_type="provider_error",
                )
                _cr._raise_structured_provider_error(provider_response)

            response_content = str(provider_response)
            used_provider = request.provider or "unknown"
            used_model = request.model or "unknown"

        usage, cost_usd, correlation_id = _cr._extract_usage_and_cost(provider_response)

        # ── Persist assistant message ─────────────────────────────────────
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

        # ── Record task + usage event (best-effort) ───────────────────────
        try:
            await record_chat_completion_task(
                user_id=current_user.id,
                conversation_id=conversation_id,
                user_message_id=message_id,
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

        visualizations = None
        if isinstance(provider_response, dict) and provider_response.get("visualizations"):
            visualizations = provider_response["visualizations"]

        return SuccessEnvelope(
            success=True,
            data=SendMessageResponse(
                message_id=response_message_id,
                response=response_content,
                provider=used_provider,
                model=used_model,
                timestamp=datetime.utcnow().isoformat(),
                usage=usage,
                cost_usd=cost_usd,
                correlation_id=correlation_id,
                visualizations=visualizations,
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        await emit_chat_message_failed(
            current_user=current_user,
            conversation_id=conversation_id,
            message_id=message_id,
            stage="unhandled",
            provider=request.provider,
            model=request.model,
            code="INTERNAL_ERROR",
            status_code=500,
            error=str(e),
            error_type=type(e).__name__,
        )
        logger.error(
            "send_message_unhandled_error",
            error=str(e),
            error_type=type(e).__name__,
            conversation_id=conversation_id,
            user_id=current_user.id,
        )
        raise HTTPException(status_code=500, detail="Failed to send message")


@router.post("/estimate-tokens", response_model=SuccessEnvelope[EstimateTokensResponse])
async def estimate_tokens(
    request: SendMessageRequest,
    conversation_id: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> SuccessEnvelope[EstimateTokensResponse]:
    """Estimate token usage and cost for a message without invoking the provider.

    Runs the same context-assembly pipeline as send_message so the estimate
    reflects what the real call would consume. Output tokens are a fixed
    OUTPUT_TOKEN_RATIO heuristic; this is a UI hint, not a guarantee.
    """
    history_messages: list[dict] = []
    if conversation_id:
        conversation = await _cr._require_owned_conversation(conversation_id, current_user)
        history_messages = [{"role": m.role, "content": m.content} for m in conversation.messages]

    layers: list[LayerEstimate] = []
    input_tokens = 0
    degraded_mode = False
    degraded_reason: Optional[str] = None

    if request.enable_context_assembly:
        try:
            assembly = await _messages_pkg._get_context_assembly_service().assemble_context(
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
                input_tokens = sum(layer.tokens for layer in layers)
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

    provider_id = resolve_provider_id(request.provider)
    if provider_id is None:
        return SuccessEnvelope(
            success=True,
            data=EstimateTokensResponse(
                input_tokens=input_tokens,
                estimated_output_tokens=estimated_output_tokens,
                estimated_cost_usd=0.0,
                provider="unknown",
                model=request.model,
                layers=layers,
                degraded_mode=True,
                degraded_reason=degraded_reason or "no-configured-providers",
            ),
        )

    provider = _messages_pkg.dispatcher.get_provider(provider_id)
    estimated_cost_usd = provider.estimate_cost(
        input_tokens,
        estimated_output_tokens,
    )

    return SuccessEnvelope(
        success=True,
        data=EstimateTokensResponse(
            input_tokens=input_tokens,
            estimated_output_tokens=estimated_output_tokens,
            estimated_cost_usd=estimated_cost_usd,
            provider=provider_id,
            model=request.model,
            layers=layers,
            degraded_mode=degraded_mode,
            degraded_reason=degraded_reason,
        ),
    )
