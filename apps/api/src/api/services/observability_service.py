"""
Observability Service for Goblin Assistant

Provides comprehensive observability and debug surfaces to prevent black box behavior.
Implements the Prime Directive: If a decision affects memory, retrieval, routing, or context,
it must be inspectable.

Key Features:
1. Write-Time Decision Logging
2. Memory Promotion Event Tracking
3. Retrieval Trace Recording
4. Context Assembly Snapshots
5. Structured Debug Endpoints
"""

import hashlib
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

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

    The Prime Directive: If a decision affects memory, retrieval, routing, or context,
    it must be inspectable. No black boxes. No "the model decided."
    """

    def __init__(self):
        self.context_assembly_service: Optional[ContextAssemblyService] = None
        self.context_monitoring_service: Optional[ContextMonitoringService] = None
        self.retrieval_service: Optional[RetrievalService] = None

        # In-memory storage (could be persisted to database)
        self.write_decisions: List[WriteTimeDecisionRecord] = []
        self.memory_promotions: List[MemoryPromotionEvent] = []
        self.retrieval_traces: List[RetrievalTrace] = []
        self.context_snapshots: List[ContextAssemblySnapshot] = []

        # Metrics tracking
        self.memory_health = {
            "avg_memories_per_user": 0,
            "promotion_rejection_rate": 0,
            "contradiction_rate": 0,
            "decay_events": 0,
        }
        self.retrieval_quality = {
            "avg_chunks_per_request": 0,
            "token_utilization_percent": 0,
            "retrieval_hit_rate": 0,
        }
        self.cost_control = {
            "embeddings_per_conversation": 0,
            "tokens_spent_per_tier": {},
            "cache_hit_rate": 0,
        }

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

    # 1. Write-Time Decision Logging
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

        This tells you why something entered the system.
        """
        try:
            classification = write_time_result.get("classification", {})
            decision = write_time_result.get("decision", {})
            write_time_result.get("execution", {})

            reason_codes = self._determine_reason_codes(
                message_content, message_role, classification, decision
            )

            decision_record = WriteTimeDecisionRecord(
                message_id=message_id,
                user_id=user_id,
                conversation_id=conversation_id,
                message_content=self._redact_content(message_content),
                message_role=message_role,
                classified_type=classification.get("type", "unknown"),
                embedded="embed" in [action.value for action in decision.get("actions", [])],
                summarized="summarize" in [action.value for action in decision.get("actions", [])],
                cached="cache" in [action.value for action in decision.get("actions", [])],
                discarded="discard" in [action.value for action in decision.get("actions", [])],
                reason_codes=reason_codes,
                confidence=classification.get("confidence", 0.0),
                timestamp=datetime.utcnow().isoformat(),
                request_id=request_id,
            )

            self.write_decisions.append(decision_record)

            logger.info(
                "Write-time decision logged",
                message_id=message_id,
                user_id=user_id,
                classified_type=decision_record.classified_type,
                embedded=decision_record.embedded,
                summarized=decision_record.summarized,
                discarded=decision_record.discarded,
                reason_codes=reason_codes,
            )

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

    # 2. Memory Promotion Event Tracking
    def log_memory_promotion_event(
        self,
        candidate_text: str,
        source: str,
        confidence_score: float,
        promotion_decision: PromotionDecision,
        rejection_reason: Optional[str],
        user_id: Optional[str],
        conversation_id: Optional[str],
        request_id: Optional[str] = None,
    ) -> None:
        """
        Log memory promotion event.

        This prevents silent personality drift and accidental profiling.
        """
        try:
            promotion_event = MemoryPromotionEvent(
                candidate_text=self._redact_content(candidate_text),
                source=source,
                confidence_score=confidence_score,
                promotion_decision=promotion_decision,
                rejection_reason=rejection_reason,
                user_id=user_id,
                conversation_id=conversation_id,
                timestamp=datetime.utcnow().isoformat(),
                request_id=request_id,
            )

            self.memory_promotions.append(promotion_event)
            self._update_memory_health_metrics()

            logger.info(
                "Memory promotion event logged",
                source=source,
                decision=promotion_decision.value,
                confidence=confidence_score,
                user_id=user_id,
                rejection_reason=rejection_reason,
            )

        except Exception as e:
            logger.error("Failed to log memory promotion event", error=str(e))

    # 3. Retrieval Trace Recording
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

        This is the crown jewel - it tells you exactly what the model saw.
        """
        try:
            items_retrieved = []
            token_allocation = {}

            layers = retrieval_result.get("layers", [])
            for layer in layers:
                tier = self._map_layer_to_tier(layer["name"])
                items_retrieved.append(
                    {
                        "source": layer["name"],
                        "tier": tier.value,
                        "relevance_score": layer.get("score", 0.0),
                        "token_count": layer["tokens"],
                        "rank": len(items_retrieved) + 1,
                        "truncated": layer["tokens"]
                        < layer.get("original_tokens", layer["tokens"]),
                    }
                )
                token_allocation[tier.value] = token_allocation.get(tier.value, 0) + layer["tokens"]

            scoring_breakdown = {
                "avg_relevance_score": sum(item["relevance_score"] for item in items_retrieved)
                / max(len(items_retrieved), 1),
                "tier_distribution": dict(token_allocation),
            }

            trace = RetrievalTrace(
                request_id=request_id,
                user_id=user_id,
                model_selected=model_selected,
                token_budget=token_budget,
                items_retrieved=items_retrieved,
                scoring_breakdown=scoring_breakdown,
                token_allocation=token_allocation,
                timestamp=datetime.utcnow().isoformat(),
            )

            self.retrieval_traces.append(trace)
            self._update_retrieval_quality_metrics()

            logger.info(
                "Retrieval trace logged",
                request_id=request_id,
                user_id=user_id,
                model=model_selected,
                total_items=len(items_retrieved),
                total_tokens=sum(token_allocation.values()),
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

    # 4. Context Assembly Snapshot
    def log_context_assembly_snapshot(
        self,
        request_id: str,
        user_id: Optional[str],
        conversation_id: Optional[str],
        context_assembly: Dict[str, Any],
    ) -> None:
        """
        Log context assembly snapshot before sending to model.

        This lets you replay bugs and compare good vs bad answers.
        """
        try:
            context_text = context_assembly.get("context", "")
            context_hash = hashlib.sha256(context_text.encode()).hexdigest()

            redacted_snapshot = {
                "layers": [
                    {
                        "name": layer["name"],
                        "token_count": layer["tokens"],
                        "source_count": layer.get("source_count", 0),
                    }
                    for layer in context_assembly.get("layers", [])
                ],
                "total_tokens": context_assembly.get("total_tokens_used", 0),
                "remaining_tokens": context_assembly.get("remaining_tokens", 0),
            }

            snapshot = ContextAssemblySnapshot(
                request_id=request_id,
                user_id=user_id,
                conversation_id=conversation_id,
                context_hash=context_hash,
                redacted_snapshot=redacted_snapshot,
                total_token_usage=context_assembly.get("total_tokens_used", 0),
                assembly_details=context_assembly.get("assembly_log", {}),
                timestamp=datetime.utcnow().isoformat(),
            )

            self.context_snapshots.append(snapshot)

            logger.info(
                "Context assembly snapshot logged",
                request_id=request_id,
                user_id=user_id,
                context_hash=context_hash[:8],
                total_tokens=snapshot.total_token_usage,
            )

        except Exception as e:
            logger.error("Failed to log context assembly snapshot", error=str(e))

    # Debug Endpoints
    def get_memory_debug_info(self, user_id: str) -> Dict[str, Any]:
        """Debug endpoint: /ops/memory/user/{id}"""
        try:
            user_promotions = [
                event
                for event in self.memory_promotions
                if event.user_id == user_id
                and event.promotion_decision == PromotionDecision.ACCEPTED
            ]

            memory_items = [
                event
                for event in user_promotions
                if event.promotion_decision == PromotionDecision.ACCEPTED
            ]

            return {
                "user_id": user_id,
                "memory_items": [
                    {
                        "content": event.candidate_text,
                        "source": event.source,
                        "confidence": event.confidence_score,
                        "timestamp": event.timestamp,
                        "source_reference": event.conversation_id,
                    }
                    for event in memory_items[-20:]
                ],
                "memory_health": {
                    "total_items": len(memory_items),
                    "avg_confidence": sum(event.confidence_score for event in memory_items)
                    / max(len(memory_items), 1),
                    "promotion_rejection_rate": self.memory_health["promotion_rejection_rate"],
                    "contradiction_rate": self.memory_health["contradiction_rate"],
                },
                "last_updated": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error("Failed to get memory debug info", user_id=user_id, error=str(e))
            return {"error": str(e)}

    def get_retrieval_trace(self, request_id: str) -> Dict[str, Any]:
        """Debug endpoint: /ops/retrieval/trace/{request_id}"""
        try:
            trace = next((t for t in self.retrieval_traces if t.request_id == request_id), None)

            if not trace:
                return {"error": f"No trace found for request_id: {request_id}"}

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
                        1 for item in trace.items_retrieved if item["truncated"]
                    ),
                    "avg_relevance_score": trace.scoring_breakdown.get("avg_relevance_score", 0),
                    "tier_efficiency": {
                        tier: count / trace.token_budget
                        for tier, count in trace.token_allocation.items()
                    },
                },
            }

        except Exception as e:
            logger.error("Failed to get retrieval trace", request_id=request_id, error=str(e))
            return {"error": str(e)}

    def get_write_decisions(self, conversation_id: str) -> Dict[str, Any]:
        """Debug endpoint: /ops/write/decisions/{conversation_id}"""
        try:
            decisions = [
                decision
                for decision in self.write_decisions
                if decision.conversation_id == conversation_id
            ]

            return {
                "conversation_id": conversation_id,
                "decisions": [
                    {
                        "message_id": decision.message_id,
                        "message_role": decision.message_role,
                        "classified_type": decision.classified_type,
                        "embedded": decision.embedded,
                        "summarized": decision.summarized,
                        "discarded": decision.discarded,
                        "reason_codes": decision.reason_codes,
                        "confidence": decision.confidence,
                        "timestamp": decision.timestamp,
                    }
                    for decision in decisions
                ],
                "summary": {
                    "total_decisions": len(decisions),
                    "embedding_rate": sum(1 for d in decisions if d.embedded)
                    / max(len(decisions), 1),
                    "summarization_rate": sum(1 for d in decisions if d.summarized)
                    / max(len(decisions), 1),
                    "discard_rate": sum(1 for d in decisions if d.discarded)
                    / max(len(decisions), 1),
                    "avg_confidence": sum(d.confidence for d in decisions) / max(len(decisions), 1),
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
            snapshot = next((s for s in self.context_snapshots if s.request_id == request_id), None)

            if not snapshot:
                return {"error": f"No snapshot found for request_id: {request_id}"}

            return {
                "request_id": snapshot.request_id,
                "user_id": snapshot.user_id,
                "context_hash": snapshot.context_hash,
                "redacted_snapshot": snapshot.redacted_snapshot,
                "total_token_usage": snapshot.total_token_usage,
                "assembly_details": snapshot.assembly_details,
                "timestamp": snapshot.timestamp,
            }

        except Exception as e:
            logger.error("Failed to get context snapshot", request_id=request_id, error=str(e))
            return {"error": str(e)}

    # Metrics and Alerts
    def get_critical_metrics(self) -> Dict[str, Any]:
        """Get metrics that actually matter for system health"""
        return {
            "memory_health": self.memory_health,
            "retrieval_quality": self.retrieval_quality,
            "cost_control": self.cost_control,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for system health alerts"""
        alerts = []

        if self.memory_health["promotion_rejection_rate"] > 0.8:
            alerts.append(
                {
                    "type": "memory_promotion_spike",
                    "severity": "warning",
                    "message": f"Memory promotion rejection rate is high: {self.memory_health['promotion_rejection_rate']:.2%}",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

        if self.retrieval_quality["retrieval_hit_rate"] < 0.1:
            alerts.append(
                {
                    "type": "retrieval_empty",
                    "severity": "critical",
                    "message": f"Retrieval hit rate is very low: {self.retrieval_quality['retrieval_hit_rate']:.2%}",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

        if self.retrieval_quality["token_utilization_percent"] > 95:
            alerts.append(
                {
                    "type": "token_budget_exceeded",
                    "severity": "warning",
                    "message": f"Token budget frequently exceeded: {self.retrieval_quality['token_utilization_percent']:.1f}%",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

        if self.memory_health["contradiction_rate"] > 0.1:
            alerts.append(
                {
                    "type": "memory_contradiction",
                    "severity": "critical",
                    "message": f"Memory contradiction rate is high: {self.memory_health['contradiction_rate']:.2%}",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

        return alerts

    def _update_memory_health_metrics(self):
        """Update memory health metrics"""
        if not self.memory_promotions:
            return

        total_promotions = len(self.memory_promotions)
        accepted = sum(
            1 for p in self.memory_promotions if p.promotion_decision == PromotionDecision.ACCEPTED
        )
        rejected = total_promotions - accepted

        self.memory_health["promotion_rejection_rate"] = (
            rejected / total_promotions if total_promotions > 0 else 0
        )

    def _update_retrieval_quality_metrics(self):
        """Update retrieval quality metrics"""
        if not self.retrieval_traces:
            return

        total_traces = len(self.retrieval_traces)
        total_items = sum(len(trace.items_retrieved) for trace in self.retrieval_traces)
        total_tokens = sum(sum(trace.token_allocation.values()) for trace in self.retrieval_traces)

        self.retrieval_quality["avg_chunks_per_request"] = (
            total_items / total_traces if total_traces > 0 else 0
        )

        total_budget = sum(trace.token_budget for trace in self.retrieval_traces)
        self.retrieval_quality["token_utilization_percent"] = (
            (total_tokens / total_budget * 100) if total_budget > 0 else 0
        )

    def _redact_content(self, content: str) -> str:
        """Redact sensitive content for logging"""
        if len(content) > 100:
            return content[:100] + "...[REDACTED]..."
        return content

    def export_observability_data(self) -> Dict[str, Any]:
        """Export all observability data for analysis"""
        return {
            "write_decisions": [asdict(d) for d in self.write_decisions[-100:]],
            "memory_promotions": [asdict(p) for p in self.memory_promotions[-50:]],
            "retrieval_traces": [asdict(t) for t in self.retrieval_traces[-20:]],
            "context_snapshots": [asdict(s) for s in self.context_snapshots[-50:]],
            "metrics": self.get_critical_metrics(),
            "alerts": self.check_alerts(),
            "export_timestamp": datetime.utcnow().isoformat(),
        }


# Global instance
observability_service = ObservabilityService()
