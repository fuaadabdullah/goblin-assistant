"""
Observability Service for Goblin Assistant

Thin facade that delegates all operations to the specialised observability/
sub-modules (decision_logger, memory_logger, retrieval_tracer,
context_snapshotter, metrics_collector, alerting_system).

Maintains full backward compatibility for all existing callers.

The Prime Directive: If a decision affects memory, retrieval, routing, or context,
it must be inspectable. No black boxes. No "the model decided."
"""

from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from ..observability.context_snapshotter import context_snapshotter
from ..observability.decision_logger import DecisionReason as ObsDecisionReason
from ..observability.decision_logger import decision_logger
from ..observability.memory_logger import memory_promotion_logger
from ..observability.metrics_collector import metrics_collector
from ..observability.retrieval_tracer import (
    RetrievedItem,
    retrieval_tracer,
)
from ..storage.database import get_db  # noqa: F401 — re-exported for test patching
from .context_assembly_service import ContextAssemblyService
from .context_monitoring import ContextMonitoringService
from .observability_models import (
    ContextAssemblySnapshot,
    DecisionReason,
    MemoryPromotionEvent,
    PromotionDecision,
    RetrievalTier,
    RetrievalTrace,
    WriteTimeDecisionRecord,
)
from .retrieval_service import RetrievalService

logger = structlog.get_logger()

# Re-export models so existing importers of observability_service continue to work
__all__ = [
    "ObservabilityService",
    "observability_service",
    "DecisionReason",
    "PromotionDecision",
    "RetrievalTier",
    "WriteTimeDecisionRecord",
    "MemoryPromotionEvent",
    "RetrievalTrace",
    "ContextAssemblySnapshot",
]


class ObservabilityService:
    """
    Central observability service for tracking all decision points.

    Now a thin facade over the dedicated observability/ sub-modules.
    The Prime Directive: If a decision affects memory, retrieval, routing, or context,
    it must be inspectable. No black boxes. No "the model decided."
    """

    def __init__(self):
        self.context_assembly_service: Optional[ContextAssemblyService] = None
        self.context_monitoring_service: Optional[ContextMonitoringService] = None
        self.retrieval_service: Optional[RetrievalService] = None
        self.write_decisions: List[WriteTimeDecisionRecord] = []
        self.memory_promotions: List[MemoryPromotionEvent] = []
        self.retrieval_traces: List[RetrievalTrace] = []
        self.context_snapshots: List[ContextAssemblySnapshot] = []

    def initialize(
        self,
        context_assembly_service: ContextAssemblyService,
        context_monitoring_service: ContextMonitoringService,
        retrieval_service: RetrievalService,
    ):
        """Initialize with required services"""
        self.context_assembly_service = context_assembly_service
        self.context_monitoring_service = context_monitoring_service
        self.retrieval_service = retrieval_service

    # ------------------------------------------------------------------
    # 1. Write-Time Decision Logging
    # ------------------------------------------------------------------
    def log_write_time_decision(
        self,
        message_id: str,
        user_id: Optional[str],
        conversation_id: Optional[str],
        message_content: str,
        message_role: str,
        write_time_result: Dict[str, Any],
        request_id: Optional[str] = None,
    ) -> None:
        """
        Log write-time decision for message processing.

        Delegates to observability.decision_logger.
        """
        try:
            classification = write_time_result.get("classification", {})
            decision = write_time_result.get("decision", {})
            actions = [a.value for a in decision.get("actions", [])]

            reason_codes = self._determine_reason_codes(
                message_content, message_role, classification, decision
            )

            # Map shared DecisionReason -> obs DecisionReason
            obs_reasons = []
            for rc in reason_codes:
                try:
                    obs_reasons.append(ObsDecisionReason(rc))
                except ValueError:
                    pass

            # Fire-and-forget via decision_logger (async but caller is sync)
            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    decision_logger.log_decision(
                        message_id=message_id,
                        conversation_id=conversation_id or "unknown",
                        user_id=user_id,
                        classified_type=classification.get("type", "unknown"),
                        embedded="embed" in actions,
                        summarized="summarize" in actions,
                        cached="cache" in actions,
                        discarded="discard" in actions,
                        reason_codes=obs_reasons,
                        confidence=classification.get("confidence", 0.0),
                        decision_metadata={
                            "write_time_result": write_time_result,
                            "message_role": message_role,
                        },
                        processing_time_ms=0.0,
                        request_id=request_id,
                    )
                )
            except RuntimeError:
                logger.debug(
                    "log_write_time_decision_no_running_loop",
                    message_id=message_id,
                )

            logger.info(
                "Write-time decision logged",
                message_id=message_id,
                classified_type=classification.get("type", "unknown"),
                reason_codes=reason_codes,
            )

            decision_payload = {
                "message_id": message_id,
                "conversation_id": conversation_id or "unknown",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "classified_type": classification.get("type", "unknown"),
                "classification": {
                    "type": classification.get("type", "unknown"),
                    "confidence": classification.get("confidence", 0.0),
                    "reason_codes": reason_codes,
                },
                "decisions": {
                    "embedded": "embed" in actions,
                    "summarized": "summarize" in actions,
                    "cached": "cache" in actions,
                    "discarded": "discard" in actions,
                },
                "message_content": message_content,
                "message_role": message_role,
                "confidence": classification.get("confidence", 0.0),
                "reason_codes": reason_codes,
                "request_id": request_id,
            }
            self.write_decisions.append(decision_payload)

        except Exception as e:
            logger.error("Failed to log write-time decision", error=str(e))

    def _determine_reason_codes(
        self,
        message_content: str,
        message_role: str,
        classification: Dict[str, Any],
        decision: Dict[str, Any],
    ) -> List[str]:
        """Determine reason codes for the decision"""
        reason_codes = []

        if message_role == "system":
            reason_codes.append(DecisionReason.SYSTEM_MESSAGE.value)
        elif message_role == "user":
            if len(message_content) < 10:
                reason_codes.append(DecisionReason.SHORT_CHAT.value)
            else:
                reason_codes.append(DecisionReason.CONTEXT_RELEVANT.value)

        message_type = classification.get("type", "")
        if message_type == "fact":
            reason_codes.append(DecisionReason.DECLARATIVE_FACT.value)
        elif message_type == "task_result":
            reason_codes.append(DecisionReason.TASK_RESULT.value)
        elif message_type == "noise":
            reason_codes.append(DecisionReason.NOISE.value)
        elif message_type == "preference":
            reason_codes.append(DecisionReason.USER_PREFERENCE.value)

        actions = [action.value for action in decision.get("actions", [])]
        if "embed" in actions:
            reason_codes.append(DecisionReason.CONTEXT_RELEVANT.value)
        if "discard" in actions:
            reason_codes.append(DecisionReason.LOW_SIGNAL.value)

        return list(set(reason_codes))

    # ------------------------------------------------------------------
    # 2. Memory Promotion Event Tracking
    # ------------------------------------------------------------------
    def log_memory_promotion_event(
        self,
        candidate_text: str,
        source: str,
        confidence_score: float,
        promotion_decision: PromotionDecision,
        rejection_reason: Optional[str],
        user_id: Optional[str],
        conversation_id: Optional[str],
        memory_state: Optional[str] = None,
        conflict_reason: Optional[str] = None,
        conflicting_memory_ids: Optional[List[str]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """
        Log memory promotion event.

        Delegates to observability.memory_logger.
        """
        try:
            # Map rejection to gates-passed/failed for the new logger
            from ..observability.memory_logger import (
                MemoryPromotionEvent as ObsMemoryPromotionEvent,  # noqa: PLC0415
            )
            from ..observability.memory_logger import PromotionGate  # noqa: PLC0415

            gates_passed = []
            gates_failed = []

            if promotion_decision == PromotionDecision.ACCEPTED:
                gates_passed = [PromotionGate.CONTENT_QUALITY, PromotionGate.STABILITY]
            else:
                gates_failed = [PromotionGate.CONTENT_QUALITY]

            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    memory_promotion_logger.log_promotion_attempt(
                        candidate_text=self._redact_content(candidate_text),
                        category=source,
                        source_conversation=conversation_id or "unknown",
                        source_type=source,
                        confidence_score=confidence_score,
                        promotion_decision=(promotion_decision == PromotionDecision.ACCEPTED),
                        gates_passed=gates_passed,
                        gates_failed=gates_failed,
                        rejection_reason=rejection_reason or conflict_reason,
                        memory_fact_id=None,
                        user_id=user_id,
                        request_id=request_id,
                        metadata={
                            "memory_state": memory_state,
                            "conflict_reason": conflict_reason,
                            "conflicting_memory_ids": list(conflicting_memory_ids or []),
                        },
                    )
                )
            except RuntimeError:
                pass

            event = ObsMemoryPromotionEvent(
                event_id=f"prom_{int(datetime.utcnow().timestamp())}_{hash(candidate_text) % 10000}",
                timestamp=datetime.utcnow(),
                candidate_text=self._redact_content(candidate_text),
                category=source,
                source_conversation=conversation_id or "unknown",
                source_type=source,
                confidence_score=confidence_score,
                promotion_decision=(promotion_decision == PromotionDecision.ACCEPTED),
                gates_passed=gates_passed,
                gates_failed=gates_failed,
                rejection_reason=rejection_reason or conflict_reason,
                memory_fact_id=None,
                user_id=user_id,
                request_id=request_id,
                metadata={
                    "memory_state": memory_state,
                    "conflict_reason": conflict_reason,
                    "conflicting_memory_ids": list(conflicting_memory_ids or []),
                },
            )
            memory_promotion_logger._promotion_cache[
                f"{event.source_conversation}:{hash(candidate_text) % 10000}"
            ] = event

            logger.info(
                "Memory promotion event logged",
                source=source,
                decision=promotion_decision.value,
                confidence=confidence_score,
            )

            self.memory_promotions.append(
                MemoryPromotionEvent(
                    candidate_text=self._redact_content(candidate_text),
                    source=source,
                    confidence_score=confidence_score,
                    promotion_decision=promotion_decision,
                    rejection_reason=rejection_reason or conflict_reason,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    timestamp=datetime.utcnow().isoformat(),
                    memory_state=memory_state,
                    conflict_reason=conflict_reason,
                    conflicting_memory_ids=list(conflicting_memory_ids or []),
                    request_id=request_id,
                )
            )

        except Exception as e:
            logger.error("Failed to log memory promotion event", error=str(e))

    # ------------------------------------------------------------------
    # 3. Retrieval Trace Recording
    # ------------------------------------------------------------------
    def log_retrieval_trace(
        self,
        request_id: str,
        user_id: Optional[str],
        model_selected: str,
        token_budget: int,
        retrieval_result: Dict[str, Any],
    ) -> None:
        """
        Log complete retrieval trace for LLM call.

        Delegates to observability.retrieval_tracer.
        """
        try:
            from ..observability.retrieval_tracer import (
                RetrievalTrace as ObsRetrievalTrace,  # noqa: PLC0415
            )

            layers = retrieval_result.get("layers", [])
            items = []
            for idx, layer in enumerate(layers):
                items.append(
                    RetrievedItem(
                        source=layer["name"],
                        source_id=None,
                        content="",
                        relevance_score=layer.get("score", 0.0),
                        token_count=layer["tokens"],
                        rank=idx + 1,
                        truncated=layer["tokens"] < layer.get("original_tokens", layer["tokens"]),
                        metadata={},
                    )
                )

            context_text = retrieval_result.get("context", "")
            context_hash = _compute_hash(context_text)

            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    retrieval_tracer.trace_retrieval(
                        request_id=request_id,
                        user_id=user_id,
                        model_selected=model_selected,
                        token_budget=token_budget,
                        items_retrieved=items,
                        context_hash=context_hash,
                        context_snapshot=context_text[:200] if context_text else "",
                        retrieval_time_ms=0.0,
                        error=None,
                    )
                )
            except RuntimeError:
                pass

            trace = ObsRetrievalTrace(
                request_id=request_id,
                user_id=user_id,
                timestamp=datetime.utcnow(),
                model_selected=model_selected,
                token_budget=token_budget,
                total_tokens_used=sum(item.token_count for item in items),
                items_retrieved=items,
                tier_breakdown={},
                context_hash=context_hash,
                context_snapshot=context_text[:200] if context_text else "",
                retrieval_time_ms=0.0,
                truncation_events=[],
                error=None,
            )
            retrieval_tracer._trace_cache[request_id] = trace

            logger.info(
                "Retrieval trace logged",
                request_id=request_id,
                total_items=len(items),
            )

            self.retrieval_traces.append(
                RetrievalTrace(
                    request_id=request_id,
                    user_id=user_id,
                    model_selected=model_selected,
                    token_budget=token_budget,
                    items_retrieved=[
                        {
                            "source": item.source,
                            "tier": item.metadata.get("tier", ""),
                            "relevance_score": item.relevance_score,
                            "token_count": item.token_count,
                            "rank": item.rank,
                            "truncated": item.truncated,
                        }
                        for item in items
                    ],
                    scoring_breakdown={},
                    token_allocation={},
                    timestamp=datetime.utcnow().isoformat(),
                )
            )

        except Exception as e:
            logger.error("Failed to log retrieval trace", error=str(e))

    def _map_layer_to_tier(self, layer_name: str) -> RetrievalTier:
        """Map layer name to retrieval tier"""
        tier_mapping = {
            "system": RetrievalTier.LONG_TERM,
            "long_term_memory": RetrievalTier.LONG_TERM,
            "working_memory": RetrievalTier.WORKING_MEMORY,
            "semantic_retrieval": RetrievalTier.SEMANTIC,
            "ephemeral_memory": RetrievalTier.EPHEMERAL,
        }
        return tier_mapping.get(layer_name, RetrievalTier.SEMANTIC)

    # ------------------------------------------------------------------
    # 4. Context Assembly Snapshot
    # ------------------------------------------------------------------
    def log_context_assembly_snapshot(
        self,
        request_id: str,
        user_id: Optional[str],
        conversation_id: Optional[str],
        context_assembly: Dict[str, Any],
    ) -> None:
        """
        Log context assembly snapshot before sending to model.

        Delegates to observability.context_snapshotter.
        """
        try:
            from ..observability.context_snapshotter import (
                ContextSnapshot as ObsContextSnapshot,  # noqa: PLC0415
            )

            context_text = context_assembly.get("context", "")
            metadata = {
                "conversation_id": conversation_id,
                "remaining_tokens": context_assembly.get("remaining_tokens", 0),
                "token_budget": context_assembly.get("token_budget", 0),
                "model_target": "unknown",
            }

            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    context_snapshotter.create_snapshot(
                        correlation_id=request_id,
                        user_id=user_id,
                        context=context_text,
                        metadata=metadata,
                        assembly_time_ms=0.0,
                    )
                )
            except RuntimeError:
                pass

            snapshot = ObsContextSnapshot(
                snapshot_id=f"ctx_{int(datetime.utcnow().timestamp())}_{hash(_compute_hash(context_text)) % 10000}",
                request_id=request_id,
                user_id=user_id,
                timestamp=datetime.utcnow(),
                context_hash=_compute_hash(context_text),
                context_layers=[{"type": "assembled_context", "content": context_text}],
                total_tokens=context_assembly.get("total_tokens_used", 0),
                remaining_tokens=context_assembly.get("remaining_tokens", 0),
                token_budget=context_assembly.get("token_budget", 0),
                model_target="unknown",
                redaction_applied=False,
                redaction_details={},
                assembly_time_ms=0.0,
                error=None,
            )
            context_snapshotter._snapshot_cache[request_id] = snapshot

            logger.info(
                "Context assembly snapshot logged",
                request_id=request_id,
            )

            self.context_snapshots.append(
                ContextAssemblySnapshot(
                    request_id=request_id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    context_hash=_compute_hash(context_text),
                    redacted_snapshot={
                        "layers": context_assembly.get("layers", []),
                        "total_tokens": context_assembly.get("total_tokens_used", 0),
                        "remaining_tokens": context_assembly.get("remaining_tokens", 0),
                    },
                    total_token_usage=context_assembly.get("total_tokens_used", 0),
                    assembly_details={},
                    timestamp=datetime.utcnow().isoformat(),
                )
            )

        except Exception as e:
            logger.error("Failed to log context assembly snapshot", error=str(e))

    # ------------------------------------------------------------------
    # Debug Endpoints — query the observability sub-modules
    # ------------------------------------------------------------------
    def get_memory_debug_info(self, user_id: str) -> Dict[str, Any]:
        """Debug endpoint: /ops/memory/user/{id}"""
        try:
            if self.memory_promotions:
                events = [
                    {
                        "candidate_text": e.candidate_text,
                        "source_type": e.source,
                        "confidence_score": e.confidence_score,
                        "timestamp": e.timestamp,
                        "source_conversation": e.conversation_id,
                    }
                    for e in self.memory_promotions
                    if e.user_id == user_id
                ]
            else:
                events = []

            # Query memory_promotion_logger for user's events
            import asyncio  # noqa: PLC0415

            # Try to get from the async logger if event loop is running
            if not events:
                try:
                    loop = asyncio.get_running_loop()
                    future = asyncio.run_coroutine_threadsafe(
                        memory_promotion_logger.get_promotion_history(user_id=user_id, limit=20),
                        loop,
                    )
                    # Short timeout — fall back to empty if it fails
                    events = future.result(timeout=2)
                except (RuntimeError, TimeoutError, Exception):
                    events = []

            return {
                "user_id": user_id,
                "memory_items": [
                    {
                        "content": e.get("candidate_text", ""),
                        "source": e.get("source_type", ""),
                        "confidence": e.get("confidence_score", 0.0),
                        "timestamp": e.get("timestamp", ""),
                        "source_reference": e.get("source_conversation", ""),
                    }
                    for e in events[-20:]
                ],
                "memory_health": {
                    "total_items": len(events),
                    "avg_confidence": (
                        sum(e.get("confidence_score", 0.0) for e in events) / max(len(events), 1)
                    ),
                    "promotion_rejection_rate": 0.0,
                    "contradiction_rate": 0.0,
                },
                "last_updated": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error("Failed to get memory debug info", user_id=user_id, error=str(e))
            return {"error": str(e)}

    def get_retrieval_trace(self, request_id: str) -> Dict[str, Any]:
        """Debug endpoint: /ops/retrieval/trace/{request_id}"""
        try:
            if self.retrieval_traces:
                trace = next(
                    (t for t in reversed(self.retrieval_traces) if t.request_id == request_id),
                    None,
                )
                if trace:
                    return {
                        "request_id": trace.request_id,
                        "user_id": trace.user_id,
                        "model_selected": trace.model_selected,
                        "token_budget": trace.token_budget,
                        "retrieval_items": trace.items_retrieved,
                        "scoring_breakdown": trace.scoring_breakdown,
                        "token_allocation": trace.token_allocation,
                        "timestamp": trace.timestamp,
                        "analysis": {
                            "items_cut_due_to_budget": sum(
                                1 for item in trace.items_retrieved if item.get("truncated")
                            ),
                            "avg_relevance_score": (
                                sum(
                                    item.get("relevance_score", 0.0)
                                    for item in trace.items_retrieved
                                )
                                / max(len(trace.items_retrieved), 1)
                            ),
                            "tier_efficiency": {},
                        },
                    }

            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_running_loop()
                future = asyncio.run_coroutine_threadsafe(
                    retrieval_tracer.get_retrieval_trace(request_id), loop
                )
                trace = future.result(timeout=2)
            except (RuntimeError, TimeoutError, Exception):
                trace = None

            if not trace:
                return {"error": f"No trace found for request_id: {request_id}"}

            return {
                "request_id": trace.get("request_id", request_id),
                "user_id": trace.get("user_id"),
                "model_selected": trace.get("model_selected", ""),
                "token_budget": trace.get("token_budget", 0),
                "retrieval_items": trace.get("items_retrieved", []),
                "scoring_breakdown": trace.get("tier_breakdown", {}),
                "token_allocation": {
                    tier: stats.get("total_tokens", 0)
                    for tier, stats in trace.get("tier_breakdown", {}).items()
                },
                "timestamp": trace.get("timestamp", ""),
                "analysis": {
                    "items_cut_due_to_budget": sum(
                        1 for item in trace.get("items_retrieved", []) if item.get("truncated")
                    ),
                    "avg_relevance_score": (
                        sum(
                            item.get("relevance_score", 0.0)
                            for item in trace.get("items_retrieved", [])
                        )
                        / max(len(trace.get("items_retrieved", [])), 1)
                    ),
                    "tier_efficiency": {},
                },
            }

        except Exception as e:
            logger.error("Failed to get retrieval trace", request_id=request_id, error=str(e))
            return {"error": str(e)}

    def get_write_decisions(self, conversation_id: str) -> Dict[str, Any]:
        """Debug endpoint: /ops/write/decisions/{conversation_id}"""
        try:
            if self.write_decisions:
                decisions = [
                    d for d in self.write_decisions if d.get("conversation_id") == conversation_id
                ]
            else:
                decisions = []

            import asyncio  # noqa: PLC0415

            if not decisions:
                try:
                    loop = asyncio.get_running_loop()
                    future = asyncio.run_coroutine_threadsafe(
                        decision_logger.get_decision_history(
                            conversation_id=conversation_id, limit=100
                        ),
                        loop,
                    )
                    decisions = future.result(timeout=2)
                except (RuntimeError, TimeoutError, Exception):
                    decisions = []

            return {
                "conversation_id": conversation_id,
                "decisions": [
                    {
                        "message_id": d.get("message_id", ""),
                        "message_role": d.get("classification", {}).get("type", "unknown"),
                        "classified_type": d.get("classification", {}).get("type", "unknown"),
                        "embedded": d.get("decisions", {}).get("embedded", False),
                        "summarized": d.get("decisions", {}).get("summarized", False),
                        "discarded": d.get("decisions", {}).get("discarded", False),
                        "reason_codes": d.get("classification", {}).get("reason_codes", []),
                        "confidence": d.get("classification", {}).get("confidence", 0.0),
                        "timestamp": d.get("timestamp", ""),
                    }
                    for d in decisions
                ],
                "summary": {
                    "total_decisions": len(decisions),
                    "embedding_rate": sum(
                        1 for d in decisions if d.get("decisions", {}).get("embedded", False)
                    )
                    / max(len(decisions), 1),
                    "summarization_rate": sum(
                        1 for d in decisions if d.get("decisions", {}).get("summarized", False)
                    )
                    / max(len(decisions), 1),
                    "discard_rate": sum(
                        1 for d in decisions if d.get("decisions", {}).get("discarded", False)
                    )
                    / max(len(decisions), 1),
                    "avg_confidence": sum(
                        d.get("classification", {}).get("confidence", 0.0) for d in decisions
                    )
                    / max(len(decisions), 1),
                },
            }

        except Exception as e:
            logger.error(
                "Failed to get write decisions",
                conversation_id=conversation_id,
                error=str(e),
            )
            return {"error": str(e)}

    def get_context_snapshot(self, request_id: str) -> Dict[str, Any]:
        """Get context assembly snapshot for a specific request"""
        try:
            if self.context_snapshots:
                snapshot = next(
                    (s for s in reversed(self.context_snapshots) if s.request_id == request_id),
                    None,
                )
                if snapshot:
                    return {
                        "request_id": snapshot.request_id,
                        "user_id": snapshot.user_id,
                        "context_hash": snapshot.context_hash,
                        "redacted_snapshot": snapshot.redacted_snapshot,
                        "total_token_usage": snapshot.total_token_usage,
                        "assembly_details": snapshot.assembly_details,
                        "timestamp": snapshot.timestamp,
                    }

            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_running_loop()
                future = asyncio.run_coroutine_threadsafe(
                    context_snapshotter.get_context_snapshot(request_id), loop
                )
                snapshot = future.result(timeout=2)
            except (RuntimeError, TimeoutError, Exception):
                snapshot = None

            if not snapshot:
                return {"error": f"No snapshot found for request_id: {request_id}"}

            return {
                "request_id": snapshot.get("request_id", request_id),
                "user_id": snapshot.get("user_id"),
                "context_hash": snapshot.get("context_hash", ""),
                "redacted_snapshot": {
                    "layers": snapshot.get("context_layers", []),
                    "total_tokens": snapshot.get("total_tokens", 0),
                    "remaining_tokens": snapshot.get("remaining_tokens", 0),
                },
                "total_token_usage": snapshot.get("total_tokens", 0),
                "assembly_details": {},
                "timestamp": snapshot.get("timestamp", ""),
            }

        except Exception as e:
            logger.error("Failed to get context snapshot", request_id=request_id, error=str(e))
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Metrics and Alerts — delegate to dedicated modules
    # ------------------------------------------------------------------
    def get_critical_metrics(self) -> Dict[str, Any]:
        """Get metrics that actually matter for system health"""
        try:
            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_running_loop()
                future = asyncio.run_coroutine_threadsafe(
                    metrics_collector.collect_system_metrics(user_id=None, time_window_hours=24),
                    loop,
                )
                metrics = future.result(timeout=2)

                metrics_data = {
                    "memory_health": {
                        "avg_memories_per_user": 0,
                        "promotion_rejection_rate": (
                            100 - (metrics.memory_health.get("score", 0) or 0)
                        )
                        / 100
                        if metrics.memory_health.get("status") != "no_data"
                        else 0,
                        "contradiction_rate": 0,
                        "decay_events": 0,
                    },
                    "retrieval_quality": {
                        "avg_chunks_per_request": metrics.retrieval_quality.get(
                            "total_retrievals", 0
                        ),
                        "token_utilization_percent": metrics.retrieval_quality.get(
                            "token_utilization", 0
                        ),
                        "retrieval_hit_rate": metrics.retrieval_quality.get("avg_relevance", 0),
                    },
                    "cost_control": {
                        "embeddings_per_conversation": 0,
                        "tokens_spent_per_tier": {},
                        "cache_hit_rate": 0,
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                }
            except (RuntimeError, TimeoutError, Exception):
                metrics_data = {
                    "memory_health": {
                        "avg_memories_per_user": 0,
                        "promotion_rejection_rate": 0,
                        "contradiction_rate": 0,
                        "decay_events": 0,
                    },
                    "retrieval_quality": {
                        "avg_chunks_per_request": 0,
                        "token_utilization_percent": 0,
                        "retrieval_hit_rate": 0,
                    },
                    "cost_control": {
                        "embeddings_per_conversation": 0,
                        "tokens_spent_per_tier": {},
                        "cache_hit_rate": 0,
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                }

            return metrics_data

        except Exception as e:
            logger.error("Failed to get critical metrics", error=str(e))
            return {
                "memory_health": {},
                "retrieval_quality": {},
                "cost_control": {},
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }

    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for system health alerts"""
        try:
            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_running_loop()
                future = asyncio.run_coroutine_threadsafe(
                    metrics_collector.collect_system_metrics(user_id=None, time_window_hours=24),
                    loop,
                )
                metrics = future.result(timeout=2)
            except (RuntimeError, TimeoutError, Exception):
                metrics = None

            alerts: List[Dict[str, Any]] = []

            if metrics:
                # Check memory health
                if metrics.memory_health.get("status") == "critical":
                    alerts.append(
                        {
                            "type": "memory_promotion_spike",
                            "severity": "warning",
                            "message": f"Memory health is critical: score={metrics.memory_health.get('score', 0)}",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

                # Check retrieval quality
                if metrics.retrieval_quality.get("status") == "critical":
                    alerts.append(
                        {
                            "type": "retrieval_empty",
                            "severity": "critical",
                            "message": f"Retrieval quality is critical: score={metrics.retrieval_quality.get('score', 0)}",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

                token_util = metrics.retrieval_quality.get("token_utilization", 0)
                if token_util > 95:
                    alerts.append(
                        {
                            "type": "token_budget_exceeded",
                            "severity": "warning",
                            "message": f"Token budget frequently exceeded: {token_util:.1f}%",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

                # Check context health
                if metrics.context_assembly.get("status") == "critical":
                    alerts.append(
                        {
                            "type": "memory_contradiction",
                            "severity": "critical",
                            "message": f"Context assembly is critical: score={metrics.context_assembly.get('score', 0)}",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

            return alerts

        except Exception as e:
            logger.error("Failed to check alerts", error=str(e))
            return [
                {
                    "type": "system_error",
                    "severity": "warning",
                    "message": f"Alert check failed: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _redact_content(self, content: str) -> str:
        """Redact sensitive content for logging"""
        if len(content) > 100:
            return content[:100] + "...[REDACTED]..."
        return content

    def export_observability_data(self) -> Dict[str, Any]:
        """Export all observability data for analysis"""
        try:
            import asyncio  # noqa: PLC0415

            decisions: List[Dict[str, Any]] = []
            promotions: List[Dict[str, Any]] = []
            retrievals: List[Dict[str, Any]] = []
            snapshots: List[Dict[str, Any]] = []

            try:
                loop = asyncio.get_running_loop()

                # Gather from all sub-modules

                futures = {
                    "decisions": asyncio.run_coroutine_threadsafe(
                        decision_logger.get_decision_history(conversation_id="", limit=100),
                        loop,
                    ),
                    "promotions": asyncio.run_coroutine_threadsafe(
                        memory_promotion_logger.get_promotion_history(limit=50),
                        loop,
                    ),
                    "retrievals": asyncio.run_coroutine_threadsafe(
                        retrieval_tracer.get_retrieval_history(limit=20),
                        loop,
                    ),
                }

                for key, future in futures.items():
                    try:
                        result = future.result(timeout=2)
                        if key == "decisions":
                            decisions = result
                        elif key == "promotions":
                            promotions = result
                        elif key == "retrievals":
                            retrievals = result
                    except (TimeoutError, Exception):
                        pass

            except (RuntimeError, Exception):
                pass

            if not decisions and self.write_decisions:
                decisions = list(self.write_decisions)
            if not promotions and self.memory_promotions:
                promotions = [asdict(item) for item in self.memory_promotions]
            if not retrievals and self.retrieval_traces:
                retrievals = [asdict(item) for item in self.retrieval_traces]
            if not snapshots and self.context_snapshots:
                snapshots = [asdict(item) for item in self.context_snapshots]

            return {
                "write_decisions": decisions,
                "memory_promotions": promotions,
                "retrieval_traces": retrievals,
                "context_snapshots": snapshots,
                "metrics": self.get_critical_metrics(),
                "alerts": self.check_alerts(),
                "export_timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error("Failed to export observability data", error=str(e))
            return {
                "write_decisions": [],
                "memory_promotions": [],
                "retrieval_traces": [],
                "context_snapshots": [],
                "metrics": {},
                "alerts": [],
                "export_timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }


def _compute_hash(text: str) -> str:
    """Compute a SHA-256 hex digest for context comparison."""
    import hashlib  # noqa: PLC0415

    return hashlib.sha256(text.encode()).hexdigest()


# Global instance
observability_service = ObservabilityService()
