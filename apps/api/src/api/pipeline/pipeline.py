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

The pipeline NEVER raises — each stage wraps in try/except and returns a safe
default context on failure. The caller always gets a PipelineResult back and
can proceed with whatever partial data is available.
"""

from __future__ import annotations

import dataclasses
import uuid
from typing import Any, Dict, List, Optional, Tuple

import structlog

from .context import (
    DecisionContext,
    ExecutionContext,
    PipelineHealth,
    PipelineResult,
    RequestContext,
    ResponseContext,
)
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
    ) -> PipelineResult:
        """Run all 4 stages in order and return a fully populated PipelineResult."""
        req = RequestContext(
            user_id=user_id,
            conversation_id=conversation_id,
            raw_message=raw_message,
            sanitized_message=sanitized_message,
        )

        dec, intent_err = await self._stage_intent(req, history_messages, intent_result)
        dec, memory_err, memory_fallback = await self._stage_memory(
            req, dec, history_messages, enable_context_assembly, request_model
        )
        exec_, routing_err, routing_fallback = await self._stage_routing(
            req, dec, history_messages, preferred_provider, preferred_model
        )
        resp, tools_err = await self._stage_tools(dec, exec_)

        first_failed = (
            "intent"
            if intent_err
            else "memory"
            if memory_err
            else "routing"
            if routing_err
            else "tools"
            if tools_err
            else None
        )
        errors = [e for e in [intent_err, memory_err, routing_err, tools_err] if e]
        health = PipelineHealth(
            error=errors[0] if errors else None,
            used_fallback=memory_fallback or routing_fallback,
            failed_stage=first_failed,
        )
        return PipelineResult(req, dec, exec_, resp, health)

    async def run_routing_only(
        self,
        *,
        sanitized_message: str,
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None,
    ) -> Tuple[DecisionContext, ExecutionContext]:
        """Run intent + routing stages only — no memory assembly, no tool selection.

        Used by the streaming path, which needs department/provider resolution
        but not the full 4-stage pipeline.
        """
        req = RequestContext(
            user_id="",
            conversation_id="",
            raw_message=sanitized_message,
            sanitized_message=sanitized_message,
        )
        dec, _ = await self._stage_intent(req, [], None)
        exec_, _, _ = await self._stage_routing(req, dec, [], preferred_provider, preferred_model)
        return dec, exec_

    # ── Stage 1: Intent ───────────────────────────────────────────────────────

    async def _stage_intent(
        self,
        req: RequestContext,
        history_messages: List[Dict[str, Any]],
        intent_result: Optional[Any],
    ) -> Tuple[DecisionContext, Optional[str]]:
        try:
            from api.routing.intent_classifier import map_intent_to_task_type  # noqa: I001

            intent = (
                intent_result
                if intent_result is not None
                else self._ic.classify(req.sanitized_message)
            )
            task_type = map_intent_to_task_type(intent) or "chat"
            complexity = self._compute_complexity(req, intent, task_type, history_messages)
            return DecisionContext(
                intent=intent, task_type=task_type, complexity_score=complexity
            ), None
        except Exception as exc:
            logger.warning("pipeline_intent_stage_failed", error=str(exc))
            return DecisionContext(), f"intent:{exc}"

    def _compute_complexity(
        self,
        req: RequestContext,
        intent: Optional[Any],
        task_type: str,
        history_messages: List[Dict[str, Any]],
    ) -> float:
        try:
            from api.routing.feature_extractor import feature_extractor  # noqa: I001

            label = intent.label.value if intent else "unknown"
            confidence = intent.confidence if intent else 0.0
            features = feature_extractor.extract_request(
                prompt=req.sanitized_message,
                task_type=task_type,
                conversation_history=history_messages,
                intent_label=label,
                intent_confidence=confidence,
            )
            return features.complexity_score
        except Exception:
            return 0.0

    # ── Stage 2: Memory / context assembly ───────────────────────────────────

    async def _stage_memory(
        self,
        req: RequestContext,
        dec: DecisionContext,
        history_messages: List[Dict[str, Any]],
        enable_context_assembly: bool,
        request_model: Optional[str],
    ) -> Tuple[DecisionContext, Optional[str], bool]:
        if not enable_context_assembly:
            return (
                dataclasses.replace(dec, context_metadata={"context_assembly_enabled": False}),
                None,
                False,
            )
        try:
            assembly_result = await self._cas.assemble_context(
                query=req.sanitized_message,
                user_id=req.user_id,
                conversation_id=req.conversation_id,
                conversation_history=history_messages[-10:],
                model=request_model,
                intent=dec.intent,
            )
            return (
                dataclasses.replace(
                    dec,
                    assembled_context=assembly_result.get("context", ""),
                    context_metadata={
                        "context_assembly_enabled": True,
                        "context_assembly_layers": len(assembly_result.get("layers", [])),
                        "total_tokens_used": assembly_result.get("total_tokens_used", 0),
                        "degraded_mode": assembly_result.get("degraded_mode", False),
                        "degraded_reason": assembly_result.get("degraded_reason"),
                        "truncation_warnings": assembly_result.get("truncation_warnings", []),
                        "summary_fallback_applied": assembly_result.get(
                            "summary_fallback_applied", False
                        ),
                        "context_snapshot_id": assembly_result.get("context_snapshot_id"),
                    },
                ),
                None,
                False,
            )
        except Exception as exc:
            logger.warning("pipeline_memory_stage_failed", error=str(exc))
            return (
                dataclasses.replace(
                    dec,
                    context_metadata={
                        "context_assembly_enabled": False,
                        "context_assembly_error": str(exc),
                    },
                ),
                f"memory:{exc}",
                True,
            )

    # ── Stage 3: Routing ──────────────────────────────────────────────────────

    async def _stage_routing(
        self,
        req: RequestContext,
        dec: DecisionContext,
        history_messages: List[Dict[str, Any]],
        preferred_provider: Optional[str],
        preferred_model: Optional[str],
    ) -> Tuple[ExecutionContext, Optional[str], bool]:
        try:
            from api.departments import classify_department  # noqa: I001

            dept_selection = classify_department(
                intent=dec.intent,
                task_type=dec.task_type,
                complexity_score=dec.complexity_score,
                preferred_provider=preferred_provider,
                preferred_model=preferred_model,
            )

            # Run the provider selection model when no explicit provider was requested.
            # This scores all candidates in the department's chain using learned feature
            # weights + Thompson Sampling, then picks the highest-scored provider.
            provider_scores: dict = {}
            routing_id: Optional[str] = None
            resolved_provider = dept_selection.resolved_provider
            resolved_model = dept_selection.resolved_model

            if not preferred_provider:
                routing_id = str(uuid.uuid4())
                scored = self._run_provider_selection(
                    req, dec, history_messages, dept_selection, routing_id=routing_id
                )
                if scored:
                    provider_scores = {s.provider_id: s.pct for s in scored}
                    # Use the top-scored provider instead of the static chain default
                    top = scored[0]
                    resolved_provider = top.provider_id
                    resolved_model = top.model_name or dept_selection.resolved_model

            # The selection model may override the department's primary, so
            # rebuild the fallback chain from the full department chain
            # (primary + fallbacks) minus whichever provider was selected.
            fallback_chain = [
                pid
                for pid in [dept_selection.resolved_provider, *dept_selection.fallback_chain]
                if pid and pid != resolved_provider
            ]

            return (
                ExecutionContext(
                    selected_department=dept_selection.department_id.value,
                    department_selection_reason=dept_selection.reason,
                    selected_provider=resolved_provider,
                    selected_model=resolved_model,
                    fallback_chain=fallback_chain,
                    provider_scores=provider_scores,
                    routing_id=routing_id,
                ),
                None,
                False,
            )
        except Exception as exc:
            logger.warning("pipeline_routing_stage_failed", error=str(exc))
            return (
                ExecutionContext(
                    selected_provider=preferred_provider,
                    selected_model=preferred_model,
                ),
                f"routing:{exc}",
                True,
            )

    def _run_provider_selection(
        self,
        req: RequestContext,
        dec: DecisionContext,
        history_messages: List[Dict[str, Any]],
        dept_selection: Any,
        *,
        routing_id: Optional[str] = None,
    ) -> list:
        """Score all department candidates via ProviderSelectionModel. Never raises."""
        try:
            from api.departments.registry import DEPARTMENT_REGISTRY  # noqa: I001
            from api.routing.feature_extractor import feature_extractor  # noqa: I001
            from api.routing.provider_selection import provider_selection_model  # noqa: I001

            policy = DEPARTMENT_REGISTRY.get(dept_selection.department_id)
            candidates = [pid for pid, _model in policy.provider_chain]
            model_map = {pid: model for pid, model in policy.provider_chain}

            label = dec.intent.label.value if dec.intent else "unknown"
            confidence = dec.intent.confidence if dec.intent else 0.0

            features = feature_extractor.extract_request(
                prompt=req.sanitized_message,
                task_type=dec.task_type or "chat",
                conversation_history=history_messages,
                intent_label=label,
                intent_confidence=confidence,
            )

            scored = provider_selection_model.score(
                candidates,
                features,
                task_type=dec.task_type or dept_selection.department_id.value,
                routing_id=routing_id,
            )

            # Attach model names from the department policy
            for s in scored:
                s.model_name = model_map.get(s.provider_id, "")

            return scored
        except Exception as exc:
            logger.debug("provider_selection_skipped", error=str(exc))
            return []

    # ── Stage 4: Tool selection ───────────────────────────────────────────────

    async def _stage_tools(
        self, dec: DecisionContext, exec_: ExecutionContext
    ) -> Tuple[ResponseContext, Optional[str]]:
        try:
            selected_names = self._tsm.select(dec.intent)

            from api.assistant_tools.registry import (  # noqa: I001
                export_tool_specs,
                format_tool_specs_for_provider,
            )

            all_specs = {spec.name: spec for spec in export_tool_specs()}
            filtered_specs = [all_specs[n] for n in selected_names if n in all_specs]
            tool_schemas = format_tool_specs_for_provider(
                filtered_specs,
                provider_id=exec_.selected_provider,
            )
            return ResponseContext(tool_candidates=selected_names, tool_schemas=tool_schemas), None
        except Exception as exc:
            logger.warning("pipeline_tools_stage_failed", error=str(exc))
            return ResponseContext(), f"tools:{exc}"
