"""GoblinOS multi-stage request pipeline.

Orchestrates the 4 pre-provider stages for every message:

    User
     ↓
    Intent Model       ← keyword classifier + cosine similarity (no GPU)
     ↓
    Memory Model       ← 5-layer context assembly (vector retrieval)
     ↓
    Routing Model      ← Thompson Sampling bandit (lightweight ML)
     ↓
    Tool Selection     ← intent-weighted scoring table (pure Python)
     ↓
    Provider           ← actual LLM call (caller's responsibility)
     ↓
    Response

None of the intermediate models require a GPU or large LLM.

The pipeline NEVER raises — each stage wraps in try/except, sets
ctx.used_fallback = True on failure, and returns a partial context.
The caller (send_message in router.py) always gets a PipelineContext back
and can proceed with whatever partial data is available.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog

from .context import PipelineContext
from .tool_selection import ToolSelectionModel

logger = structlog.get_logger()


class RequestPipeline:
    """Stateless orchestrator — holds references to the 4 stage models.

    Constructed once per app lifetime via service_accessors._get_request_pipeline().
    All stage methods are safe to call concurrently from different requests.
    """

    def __init__(
        self,
        intent_classifier: Any,
        context_assembly_service: Any,
        smart_router: Any,
        tool_selection_model: ToolSelectionModel,
    ) -> None:
        self._ic = intent_classifier
        self._cas = context_assembly_service
        self._router = smart_router
        self._tsm = tool_selection_model

    async def run(
        self,
        *,
        raw_message: str,
        sanitized_message: str,
        user_id: str,
        conversation_id: str,
        history_messages: List[Dict[str, Any]],
        intent_result: Any = None,  # IntentResult — pass pre-classified to skip _stage_intent
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None,
        enable_context_assembly: bool = True,
        request_model: Optional[str] = None,
    ) -> PipelineContext:
        """Run all 4 stages in order and return a fully populated PipelineContext."""
        ctx = PipelineContext(
            user_id=user_id,
            conversation_id=conversation_id,
            raw_message=raw_message,
            sanitized_message=sanitized_message,
        )

        if intent_result is not None:
            self._apply_preclassified_intent(ctx, intent_result, history_messages)
        else:
            await self._stage_intent(ctx, history_messages)

        await self._stage_memory(ctx, history_messages, enable_context_assembly, request_model)
        await self._stage_routing(ctx, history_messages, preferred_provider, preferred_model)
        await self._stage_tools(ctx)

        return ctx

    # ── Stage 1: Intent ───────────────────────────────────────────────────────

    def _apply_preclassified_intent(
        self,
        ctx: PipelineContext,
        intent_result: Any,
        history_messages: List[Dict[str, Any]],
    ) -> None:
        """Use a caller-supplied IntentResult (avoids duplicate classification)."""
        from api.routing.intent_classifier import map_intent_to_task_type  # noqa: I001 — lazy import

        ctx.intent = intent_result
        ctx.task_type = map_intent_to_task_type(intent_result) or "chat"
        self._compute_complexity(ctx, history_messages)

    async def _stage_intent(
        self,
        ctx: PipelineContext,
        history_messages: List[Dict[str, Any]],
    ) -> None:
        try:
            from api.routing.intent_classifier import map_intent_to_task_type  # noqa: I001 — lazy import

            intent = self._ic.classify(ctx.sanitized_message)
            ctx.intent = intent
            ctx.task_type = map_intent_to_task_type(intent) or "chat"
            self._compute_complexity(ctx, history_messages)
        except Exception as exc:
            logger.warning("pipeline_intent_stage_failed", error=str(exc))
            ctx.pipeline_error = f"intent:{exc}"

    def _compute_complexity(
        self,
        ctx: PipelineContext,
        history_messages: List[Dict[str, Any]],
    ) -> None:
        try:
            from api.routing.feature_extractor import feature_extractor  # noqa: I001 — lazy import

            label = ctx.intent.label.value if ctx.intent else "unknown"
            confidence = ctx.intent.confidence if ctx.intent else 0.0
            features = feature_extractor.extract_request(
                prompt=ctx.sanitized_message,
                task_type=ctx.task_type or "chat",
                conversation_history=history_messages,
                intent_label=label,
                intent_confidence=confidence,
            )
            ctx.complexity_score = features.complexity_score
        except Exception:
            pass  # complexity_score stays 0.0 — non-critical

    # ── Stage 2: Memory / context assembly ───────────────────────────────────

    async def _stage_memory(
        self,
        ctx: PipelineContext,
        history_messages: List[Dict[str, Any]],
        enable_context_assembly: bool,
        request_model: Optional[str],
    ) -> None:
        if not enable_context_assembly:
            ctx.context_metadata = {"context_assembly_enabled": False}
            return
        try:
            assembly_result = await self._cas.assemble_context(
                query=ctx.sanitized_message,
                user_id=ctx.user_id,
                conversation_id=ctx.conversation_id,
                conversation_history=history_messages[-10:],
                model=request_model,
                intent=ctx.intent,
            )
            ctx.assembled_context = assembly_result.get("context", "")
            ctx.context_metadata = {
                "context_assembly_enabled": True,
                "context_assembly_layers": len(assembly_result.get("layers", [])),
                "total_tokens_used": assembly_result.get("total_tokens_used", 0),
                "degraded_mode": assembly_result.get("degraded_mode", False),
                "degraded_reason": assembly_result.get("degraded_reason"),
                "truncation_warnings": assembly_result.get("truncation_warnings", []),
                "summary_fallback_applied": assembly_result.get("summary_fallback_applied", False),
                "context_snapshot_id": assembly_result.get("context_snapshot_id"),
            }
        except Exception as exc:
            logger.warning("pipeline_memory_stage_failed", error=str(exc))
            ctx.context_metadata = {
                "context_assembly_enabled": False,
                "context_assembly_error": str(exc),
            }
            ctx.used_fallback = True

    # ── Stage 3: Routing ──────────────────────────────────────────────────────

    async def _stage_routing(
        self,
        ctx: PipelineContext,
        history_messages: List[Dict[str, Any]],
        preferred_provider: Optional[str],
        preferred_model: Optional[str],
    ) -> None:
        try:
            selection = await self._router.select_provider(
                messages=history_messages,
                preferred_provider=preferred_provider,
                task_type=ctx.task_type,
                intent=ctx.intent,
                user_id=ctx.user_id,
            )
            ctx.selected_provider = selection.provider_id
            ctx.selected_model = preferred_model or selection.model
            ctx.provider_selection_reason = selection.reason
            ctx.fallback_chain = selection.fallback_chain
        except Exception as exc:
            logger.warning("pipeline_routing_stage_failed", error=str(exc))
            ctx.selected_provider = preferred_provider
            ctx.selected_model = preferred_model
            ctx.used_fallback = True

    # ── Stage 4: Tool selection ───────────────────────────────────────────────

    async def _stage_tools(self, ctx: PipelineContext) -> None:
        try:
            selected_names = self._tsm.select(ctx)
            ctx.tool_candidates = selected_names

            from api.assistant_tools.registry import (
                export_tool_specs,
                format_tool_specs_for_provider,
            )  # noqa: I001 — lazy import

            all_specs = {spec.name: spec for spec in export_tool_specs()}
            filtered_specs = [all_specs[n] for n in selected_names if n in all_specs]
            ctx.tool_schemas = format_tool_specs_for_provider(
                filtered_specs,
                provider_id=ctx.selected_provider,
            )
        except Exception as exc:
            logger.warning("pipeline_tools_stage_failed", error=str(exc))
            ctx.tool_candidates = []
            ctx.tool_schemas = []
