"""Route handlers for the send-message pipeline.

Pipeline stages are decomposed as module-level async helper functions
so the route itself reads as a high-level orchestration. Each stage
has a single responsibility and an explicit side-effect contract.
"""

import uuid
from datetime import datetime
from importlib import import_module
from inspect import isawaitable
from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ...assistant_tools.executor import extract_tool_calls_contract, run_tool_loop
from ...auth.router import User as AuthenticatedUser
from ...auth.router import get_current_user
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
from .error_mapping import provider_error_code, provider_error_status_code
from .pipeline_helpers import (
    merge_attachment_metadata,
    normalize_provider_response,
    provider_supports_tools,
    resolve_provider_id,
)
from .rovo_task import create_rovo_task, update_rovo_task
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


async def _resolve_provider_call(result: Any) -> Any:
    if isawaitable(result):
        return await result
    return result


# ---------------------------------------------------------------------------
# Private pipeline stage helpers
# ---------------------------------------------------------------------------


async def _classify_intent(message: str) -> tuple[Any, dict]:
    """Run intent classification; return (result, meta_dict) or (None, {}) on failure."""
    try:
        from api.routing.intent_classifier import intent_classifier as _ic  # noqa: PLC0415

        result = _ic.classify(message)
        return result, result.to_dict()
    except Exception as exc:
        logger.warning("intent_classification_failed", error=str(exc))
        return None, {}


async def _run_wti_stage(
    message_id: str,
    content: str,
    conversation: Any,
    conversation_id: str,
    user_id: str,
    metadata: Optional[dict],
    intent_result: Any,
) -> dict:
    """Run Write-Time Intelligence; return populated metadata dict or partial dict on failure."""
    result: dict = {}
    try:
        wti = _messages_pkg._get_write_time_intelligence()
        wti_result = await wti.process_message(
            message_id=message_id,
            content=content,
            role="user",
            user_id=conversation.user_id,
            conversation_id=conversation_id,
            metadata=metadata,
            intent=intent_result,
        )
        classification = wti_result["classification"]
        decision = wti_result["decision"]
        execution = wti_result["execution"]
        result.update(
            {
                "classification": classification,
                "decision": decision,
                "write_time_execution": execution,
                "memory_type": classification["type"],
                "confidence": classification["confidence"],
                "actions_taken": execution["actions_executed"],
                "processed_at": wti_result["processed_at"],
            }
        )
    except Exception as exc:
        logger.error(
            "write_time_intelligence_failed",
            message_id=message_id,
            conversation_id=conversation_id,
            user_id=user_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        result["write_time_error"] = str(exc)
    return result


async def _check_usage_quota(user_id: str, conversation_id: str) -> None:
    """Raise HTTP 429 if the user has exceeded daily limits; silently pass on store errors."""
    try:
        usage_store = await _messages_pkg.get_usage_event_store()
        quota = await usage_store.check_limits(user_id)
        if not quota.get("allowed", True):
            raise HTTPException(
                status_code=429,
                detail={
                    "message": "Daily usage limit exceeded",
                    "reason": quota.get("reason"),
                    "usage": quota.get("usage"),
                },
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(
            "usage_quota_check_failed",
            conversation_id=conversation_id,
            user_id=user_id,
            error=str(exc),
        )


async def _resolve_addendum(
    mode: Optional[str],
    new_category: Optional[str],
    intent_meta: dict,
    user_id: str,
    sanitized_message: str,
) -> str:
    """Return the system-prompt addendum for the request."""
    if mode:
        try:
            return _get_mode_addendum(mode)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    message_classifier, MessageType = _messages_pkg._get_message_classifier()
    classification = message_classifier.classify_message(sanitized_message, "user")
    addendum = (
        EDUCATION_SYSTEM_ADDENDUM if classification.message_type == MessageType.LEARNING else ""
    )

    if new_category:
        try:
            from api.config.mode_addendums import CATEGORY_ADDENDUMS  # noqa: PLC0415

            cat_addendum = CATEGORY_ADDENDUMS.get(new_category, "")
            if cat_addendum:
                addendum = (addendum + "\n\n" + cat_addendum).strip()
        except Exception:
            pass

    try:
        from api.config.mode_addendums import response_length_addendum as _rla  # noqa: PLC0415
        from api.services.preference_learner import preference_learner as _pl  # noqa: PLC0415

        length_pref = await _pl.get_length_pref(str(user_id), intent_meta.get("label", "default"))
        len_addendum = _rla(length_pref)
        if len_addendum:
            addendum = (addendum + "\n\n" + len_addendum).strip()
    except Exception:
        pass

    return addendum


def _log_missing_mode_tools(
    provider: Optional[str],
    mode: Optional[str],
    registered_tools: list,
) -> None:
    """Warn when mode-required tools are absent from the registered tool list."""
    if not registered_tools:
        return
    if _is_general_assistant_mode(mode):
        missing = _missing_general_assistant_tools(registered_tools)
        if missing:
            logger.warning(
                "general_assistant_required_tools_missing",
                provider=provider,
                mode=mode,
                missing_tools=missing,
                registered_tool_count=len(registered_tools),
            )
    if _is_deep_research_mode(mode):
        missing = _missing_deep_research_tools(registered_tools)
        if missing:
            logger.warning(
                "deep_research_required_tools_missing",
                provider=provider,
                mode=mode,
                missing_tools=missing,
                registered_tool_count=len(registered_tools),
            )


# ---------------------------------------------------------------------------
# Route handlers
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
            provider=request.provider or request.department,
            model=request.model,
        )

        conversation = await _cr._require_owned_conversation(conversation_id, current_user)
        sanitized_message, message_validation = _cr.InputSanitizer.sanitize_chat_message(
            request.message
        )
        message_id = str(uuid.uuid4())

        # Stage 1: Intent classification + Write-Time Intelligence
        intent_result, intent_meta = await _classify_intent(sanitized_message)
        message_metadata = await _run_wti_stage(
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
        await _check_usage_quota(current_user.id, conversation_id)

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

        addendum = await _resolve_addendum(
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
            pipeline_result.response.tool_schemas
            if provider_supports_tools(resolved_provider)
            else []
        )
        _log_missing_mode_tools(request.provider, request.mode, registered_tools)

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

        rovo_task_id = await create_rovo_task(
            resolved_provider,
            sanitized_message,
            conversation_id,
            str(current_user.id),
            pipeline_result.decision.complexity_score,
            intent_meta,
        )
        provider_response = await _resolve_provider_call(
            _cr.invoke_provider(
                pid=resolved_provider,
                model=request.model,
                payload=payload,
                timeout_ms=30000,
                stream=False,
            )
        )

        # Department chain fallback: when the user didn't pin a provider and the
        # selected one failed, walk the rest of the chain before giving up.
        if (
            not request.provider
            and isinstance(provider_response, dict)
            and not provider_response.get("ok", False)
            and "choices" not in provider_response
        ):
            for fallback_pid in pipeline_result.execution.fallback_chain:
                if fallback_pid == resolved_provider:
                    continue
                logger.warning(
                    "chat_department_fallback",
                    department=resolved_department,
                    failed_provider=resolved_provider,
                    fallback_provider=fallback_pid,
                    error=str(provider_response.get("error", "unknown")),
                )
                # Don't pin the failed provider's model on the fallback provider.
                fallback_payload = dict(payload)
                fallback_payload.pop("model", None)
                fallback_response = await _resolve_provider_call(
                    _cr.invoke_provider(
                        pid=fallback_pid,
                        model=None,
                        payload=fallback_payload,
                        timeout_ms=30000,
                        stream=False,
                    )
                )
                if isinstance(fallback_response, dict):
                    provider_response = fallback_response
                    if fallback_response.get("ok", False):
                        resolved_provider = fallback_pid
                        break

        await update_rovo_task(rovo_task_id, provider_response)

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
                provider=resolved_provider,
                model=request.model,
                tools=registered_tools,
                timeout_ms=30000,
                user_id=current_user.id,
                conversation_id=conversation_id,
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

        # Stage 7: Persist assistant message
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

        # Record task + usage event (best-effort)
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

        # Preference learning (fire-and-forget)
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

        # Track feedback outcomes (fire-and-forget)
        try:
            import asyncio as _asyncio  # noqa: PLC0415

            from api.services.feedback_service import (  # noqa: PLC0415
                FeedbackContext,
                feedback_service,
            )

            # 1. Detect continuation: find the previous assistant message and mark it
            #    as having had the conversation continue after it
            if len(history_messages) >= 2:
                prev_msgs = history_messages[:-1]  # exclude the current user message
                # Find last assistant message in history
                for i in range(len(prev_msgs) - 1, -1, -1):
                    if prev_msgs[i].get("role") == "assistant":
                        prev_asst_msg_id = None
                        # Find the corresponding message id from the store
                        if hasattr(conversation, "messages") and i < len(conversation.messages):
                            prev_msg_obj = conversation.messages[i]
                            if hasattr(prev_msg_obj, "message_id"):
                                prev_asst_msg_id = prev_msg_obj.message_id

                        if prev_asst_msg_id:
                            context = FeedbackContext(
                                user_id=str(current_user.id),
                                conversation_id=conversation_id,
                                message_id=prev_asst_msg_id,
                                request_id=correlation_id,
                                department=resolved_department,
                                provider=used_provider,
                                model=used_model,
                                task_type=pipeline_result.decision.task_type or "",
                                intent_label=intent_meta.get("label"),
                                complexity_score=pipeline_result.decision.complexity_score,
                            )
                            _prev_task = _asyncio.create_task(
                                feedback_service.record_conversation_continued(
                                    context=context,
                                    next_message_id=response_message_id,
                                )
                            )
                            _prev_task.add_done_callback(lambda _t: None)
                        break

            # 2. Detect provider/model switch
            if len(history_messages) >= 2:
                # Check the previous assistant message's metadata for provider/model
                prev_provider = None
                prev_model = None
                for j in range(len(history_messages) - 1, -1, -1):
                    if history_messages[j].get("role") == "assistant":
                        if hasattr(conversation, "messages") and j < len(conversation.messages):
                            prev_msg_obj = conversation.messages[j]
                            if hasattr(prev_msg_obj, "metadata_") and prev_msg_obj.metadata_:
                                prev_provider = prev_msg_obj.metadata_.get("provider")
                                prev_model = prev_msg_obj.metadata_.get("model")
                        break

                if prev_provider and prev_provider != used_provider:
                    # Find the assistant message id from the metadata
                    switch_asst_msg_id = None
                    for j in range(len(history_messages) - 1, -1, -1):
                        if history_messages[j].get("role") == "assistant":
                            if hasattr(conversation, "messages") and j < len(conversation.messages):
                                prev_msg_obj = conversation.messages[j]
                                if hasattr(prev_msg_obj, "message_id"):
                                    switch_asst_msg_id = prev_msg_obj.message_id
                            break

                    if switch_asst_msg_id:
                        switch_context = FeedbackContext(
                            user_id=str(current_user.id),
                            conversation_id=conversation_id,
                            message_id=switch_asst_msg_id,
                            request_id=correlation_id,
                            department=resolved_department,
                            provider=prev_provider,
                            model=prev_model,
                            task_type=pipeline_result.decision.task_type or "",
                            intent_label=intent_meta.get("label"),
                            complexity_score=pipeline_result.decision.complexity_score,
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

            # 3. Detect regeneration: if the last message in conversation history
            #    (excluding current user message) is a user message with the same content,
            #    and the assistant response was removed
            if len(history_messages) >= 2:
                # Find if there was a previous assistant message that was removed
                # (i.e., the last messages were user + assistant, and now it's just user again)
                last_user_idx = -1
                for k in range(len(history_messages) - 1, -1, -1):
                    if history_messages[k].get("role") == "user":
                        last_user_idx = k
                        break

                if last_user_idx > 0 and last_user_idx < len(history_messages) - 1:
                    # The last item in history should be an assistant message if no regeneration
                    # If history_messages[-1] is assistant, this is a normal continuation (already tracked)
                    # If the assistant after last_user_idx was removed, we detect it
                    pass  # Regeneration is better detected from the frontend sending a flag

        except Exception as exc:
            logger.debug("feedback_outcome_tracking_failed error=%s", exc)

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
