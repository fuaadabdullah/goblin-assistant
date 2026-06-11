"""Route handlers for the send-message pipeline.

The route itself is a high-level orchestration; the pipeline stages live
in sibling modules:

- `stages.py` — pre-dispatch helpers (intent, WTI, quota, addendum)
- `dispatch.py` — provider invoke, department fallback chain, tool loop
- `post_response.py` — persistence, usage recording, learning tasks
"""

import uuid
from datetime import datetime
from importlib import import_module
from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ...auth.router import User as AuthenticatedUser
from ...auth.router import get_current_user
from ...config.system_prompt import system_prompt_manager
from ...core.contracts import SuccessEnvelope
from ...providers.base import ProviderErrorCategory
from ...services.pdf_extraction_service import build_attachment_context
from .. import _runtime as _cr
from ..schemas import (
    EstimateTokensResponse,
    LayerEstimate,
    SendMessageRequest,
    SendMessageResponse,
)
from ..uploads import _pending_uploads
from .attachment_utils import attachment_context_limits, inject_attachment_context
from .dispatch import dispatch_with_fallback
from .error_mapping import provider_error_code, provider_error_status_code
from .pipeline_helpers import (
    merge_attachment_metadata,
    normalize_provider_response,
    provider_supports_tools,
    resolve_provider_id,
)
from .post_response import (
    persist_assistant_message,
    record_completion_artifacts,
    schedule_feedback_outcomes,
    schedule_preference_learning,
)
from .sentry_context import set_sentry_chat_context
from .stages import (
    check_usage_quota,
    classify_intent,
    ensure_mode_required_tools,
    log_missing_mode_tools,
    resolve_addendum,
    run_wti_stage,
)
from .usage_tracker import (
    emit_chat_message_created,
    emit_chat_message_failed,
)

OUTPUT_TOKEN_RATIO = 0.4

logger = structlog.get_logger()

router = APIRouter()
_messages_pkg = import_module(__package__)


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
            provider=request.provider or request.department,
            model=request.model,
        )

        conversation = await _cr._require_owned_conversation(conversation_id, current_user)
        sanitized_message, message_validation = _cr.InputSanitizer.sanitize_chat_message(
            request.message
        )
        message_id = str(uuid.uuid4())

        # Stage 1: Intent classification + Write-Time Intelligence
        intent_result, intent_meta = await classify_intent(sanitized_message)
        message_metadata = await run_wti_stage(
            message_id,
            sanitized_message,
            conversation,
            conversation_id,
            current_user.id,
            request.metadata,
            intent_result,
        )
        message_metadata["input_validation"] = message_validation
        if intent_meta:
            message_metadata["intent"] = intent_meta
        if request.metadata:
            message_metadata.update(request.metadata)

        # Stage 2: Attachments
        attachments_meta, attachment_context_sources = merge_attachment_metadata(
            current_user_id=current_user.id,
            attachment_ids=request.attachment_ids,
            pending_uploads=_pending_uploads,
        )
        attachment_context = ""
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

        # Stage 3: Conversation classification
        _new_category: Optional[str] = None
        try:
            from api.services.conversation_classifier import conversation_classifier as _cc  # noqa: PLC0415, I001

            _existing_category = conversation.metadata.get("category")
            _new_category = _cc.classify(sanitized_message, existing=_existing_category)
            if _new_category and _new_category != _existing_category:
                await _cr.conversation_store.update_metadata(
                    conversation_id, {"category": _new_category}
                )
            message_metadata["conversation_category"] = _new_category
        except Exception:
            pass

        # Persist user message
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

        # Quota check
        await check_usage_quota(current_user.id, conversation_id)

        # Stage 4: Context assembly + system prompt
        conversation = await _cr._require_owned_conversation(conversation_id, current_user)
        history_messages = [
            {"role": msg.role, "content": msg.content} for msg in conversation.messages
        ]

        # Resolve department → provider for backward compat
        _resolved_dept_provider: Optional[str] = None
        _resolved_dept_model: Optional[str] = None
        if request.department and not request.provider:
            try:
                from api.departments import department_dispatcher  # noqa: PLC0415

                _resolved_dept_id = department_dispatcher.resolve_provider_id(request.department)
                _resolved_dept_provider = _resolved_dept_id
            except Exception:
                pass

        pipeline_result = await _messages_pkg._get_request_pipeline().run(
            raw_message=request.message,
            sanitized_message=sanitized_message,
            user_id=str(current_user.id),
            conversation_id=conversation_id,
            history_messages=history_messages,
            intent_result=intent_result,
            preferred_provider=request.provider or _resolved_dept_provider,
            preferred_model=request.model or _resolved_dept_model,
            enable_context_assembly=request.enable_context_assembly,
            request_model=request.model,
        )
        context_metadata: Dict[str, Any] = pipeline_result.decision.context_metadata

        addendum = await resolve_addendum(
            request.mode, _new_category, intent_meta, current_user.id, sanitized_message
        )
        system_prompt = system_prompt_manager.get_complete_prompt_with_addendum(
            context=pipeline_result.decision.assembled_context,
            user_query=sanitized_message,
            addendum=addendum,
        )
        messages = [{"role": "system", "content": system_prompt}] + history_messages
        inject_attachment_context(messages, attachment_context)

        # Stage 5: Provider dispatch — use department routing
        resolved_provider = request.provider or pipeline_result.execution.selected_provider
        resolved_department = (
            request.department or pipeline_result.execution.selected_department or "general"
        )
        department_reason = pipeline_result.execution.department_selection_reason or ""
        registered_tools = (
            ensure_mode_required_tools(
                resolved_provider, request.mode, pipeline_result.response.tool_schemas
            )
            if provider_supports_tools(resolved_provider)
            else []
        )
        log_missing_mode_tools(request.provider, request.mode, registered_tools)

        payload: Dict[str, Any] = {
            "messages": messages,
            "model": request.model,
            "user_id": str(current_user.id),
            "intent": intent_meta or {},
        }
        if registered_tools:
            payload["tools"] = registered_tools

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
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
            )

        provider_response, resolved_provider = await dispatch_with_fallback(
            resolved_provider=resolved_provider,
            resolved_department=resolved_department,
            pinned_provider=request.provider,
            model=request.model,
            payload=payload,
            fallback_chain=pipeline_result.execution.fallback_chain,
            sanitized_message=sanitized_message,
            conversation_id=conversation_id,
            user_id=str(current_user.id),
            complexity_score=pipeline_result.decision.complexity_score,
            intent_meta=intent_meta,
            registered_tools=registered_tools,
            messages=messages,
        )

        # Stage 6: Normalize response (emit structured error first if provider failed)
        if (
            isinstance(provider_response, dict)
            and not provider_response.get("ok")
            and "choices" not in provider_response
        ):
            category = str(
                provider_response.get("error_category") or ProviderErrorCategory.UNKNOWN.value
            )
            await emit_chat_message_failed(
                current_user=current_user,
                conversation_id=conversation_id,
                message_id=message_id,
                stage="provider",
                provider=str(provider_response.get("provider") or request.provider or "unknown"),
                model=str(provider_response.get("model") or request.model or "unknown"),
                category=category,
                code=provider_error_code(category),
                status_code=provider_error_status_code(category),
                error=str(provider_response.get("error") or "unknown-error"),
                error_type="provider_error",
            )
            _cr._raise_structured_provider_error(provider_response)

        response_content, used_provider, used_model = normalize_provider_response(
            provider_response, request.provider, request.model
        )
        usage, cost_usd, correlation_id = _cr._extract_usage_and_cost(provider_response)

        # Stage 7: Persist assistant message + record artifacts
        response_message_id = await persist_assistant_message(
            conversation_id=conversation_id,
            current_user=current_user,
            response_content=response_content,
            used_provider=used_provider,
            used_model=used_model,
            context_metadata=context_metadata,
            usage=usage,
            cost_usd=cost_usd,
            correlation_id=correlation_id,
        )
        await record_completion_artifacts(
            current_user=current_user,
            conversation_id=conversation_id,
            user_message_id=message_id,
            response_message_id=response_message_id,
            sanitized_message=sanitized_message,
            response_content=response_content,
            used_provider=used_provider,
            used_model=used_model,
            usage=usage,
            cost_usd=cost_usd,
            correlation_id=correlation_id,
        )

        # Fire-and-forget learning tasks
        schedule_preference_learning(
            current_user=current_user,
            used_provider=used_provider,
            used_model=used_model,
            intent_meta=intent_meta,
            usage=usage,
        )
        schedule_feedback_outcomes(
            current_user=current_user,
            conversation=conversation,
            conversation_id=conversation_id,
            history_messages=history_messages,
            response_message_id=response_message_id,
            correlation_id=correlation_id,
            resolved_department=resolved_department,
            used_provider=used_provider,
            used_model=used_model,
            task_type=pipeline_result.decision.task_type or "",
            intent_meta=intent_meta,
            complexity_score=pipeline_result.decision.complexity_score,
        )

        visualizations = None
        if isinstance(provider_response, dict) and provider_response.get("visualizations"):
            visualizations = provider_response["visualizations"]

        return SuccessEnvelope(
            success=True,
            data=SendMessageResponse(
                message_id=response_message_id,
                response=response_content,
                department=resolved_department,
                department_reason=department_reason,
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

    # Resolve department for estimation
    _estimate_department = "general"
    if request.department:
        _estimate_department = request.department
    elif request.provider:
        _estimate_department = "general"  # provider was specified directly

    provider_id = resolve_provider_id(request.provider)
    if provider_id is None:
        return SuccessEnvelope(
            success=True,
            data=EstimateTokensResponse(
                input_tokens=input_tokens,
                estimated_output_tokens=estimated_output_tokens,
                estimated_cost_usd=0.0,
                department=_estimate_department,
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
            department=_estimate_department,
            layers=layers,
            degraded_mode=degraded_mode,
            degraded_reason=degraded_reason,
        ),
    )
