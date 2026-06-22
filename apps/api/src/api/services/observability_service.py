"""
Observability Service for Goblin Assistant.

Compatibility facade over the dedicated observability facets.
Preserves the public singleton, module re-exports, mutable debug surfaces,
and module-level patch seams used by legacy callers and tests.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog

from ..storage.database import get_db  # noqa: F401 - re-exported for test patching
from .context_assembly_service import ContextAssemblyService
from .context_monitoring import ContextMonitoringService
from .observability_facets import (
    ContextSnapshotFacet,
    MemoryPromotionFacet,
    ObservabilityDashboardFacet,
    RetrievalTraceFacet,
    WriteTimeFacet,
    compute_hash,
    map_layer_to_tier,
    redact_content,
)
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
    """Central observability service with stable legacy entrypoints."""

    def __init__(self):
        self.context_assembly_service: Optional[ContextAssemblyService] = None
        self.context_monitoring_service: Optional[ContextMonitoringService] = None
        self.retrieval_service: Optional[RetrievalService] = None
        self.write_decisions: List[Dict[str, Any]] = []
        self.memory_promotions: List[MemoryPromotionEvent] = []
        self.retrieval_traces: List[RetrievalTrace] = []
        self.context_snapshots: List[ContextAssemblySnapshot] = []
        self.memory_health: Dict[str, Any] = {
            "promotion_rejection_rate": 0.0,
            "contradiction_rate": 0.0,
            "decay_events": 0,
        }
        self.retrieval_quality: Dict[str, Any] = {
            "avg_chunks_per_request": 0,
            "token_utilization_percent": 0,
            "retrieval_hit_rate": 0,
        }
        self.cost_control: Dict[str, Any] = {
            "embeddings_per_conversation": 0,
            "tokens_spent_per_tier": {},
            "cache_hit_rate": 0,
        }
        self._write_time_facet = WriteTimeFacet(self)
        self._memory_promotion_facet = MemoryPromotionFacet(self)
        self._retrieval_trace_facet = RetrievalTraceFacet(self)
        self._context_snapshot_facet = ContextSnapshotFacet(self)
        self._dashboard_facet = ObservabilityDashboardFacet(self)

    def initialize(
        self,
        context_assembly_service: ContextAssemblyService,
        context_monitoring_service: ContextMonitoringService,
        retrieval_service: RetrievalService,
    ):
        self.context_assembly_service = context_assembly_service
        self.context_monitoring_service = context_monitoring_service
        self.retrieval_service = retrieval_service

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
        self._write_time_facet.log_write_time_decision(
            message_id=message_id,
            user_id=user_id,
            conversation_id=conversation_id,
            message_content=message_content,
            message_role=message_role,
            write_time_result=write_time_result,
            request_id=request_id,
        )

    def _determine_reason_codes(
        self,
        message_content: str,
        message_role: str,
        classification: Dict[str, Any],
        decision: Dict[str, Any],
    ) -> List[str]:
        return self._write_time_facet._determine_reason_codes(
            message_content=message_content,
            message_role=message_role,
            classification=classification,
            decision=decision,
        )

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
        self._memory_promotion_facet.log_memory_promotion_event(
            candidate_text=candidate_text,
            source=source,
            confidence_score=confidence_score,
            promotion_decision=promotion_decision,
            rejection_reason=rejection_reason,
            user_id=user_id,
            conversation_id=conversation_id,
            memory_state=memory_state,
            conflict_reason=conflict_reason,
            conflicting_memory_ids=conflicting_memory_ids,
            request_id=request_id,
        )

    def log_retrieval_trace(
        self,
        request_id: str,
        user_id: Optional[str],
        model_selected: str,
        token_budget: int,
        retrieval_result: Dict[str, Any],
    ) -> None:
        self._retrieval_trace_facet.log_retrieval_trace(
            request_id=request_id,
            user_id=user_id,
            model_selected=model_selected,
            token_budget=token_budget,
            retrieval_result=retrieval_result,
        )

    def _map_layer_to_tier(self, layer_name: str) -> RetrievalTier:
        return map_layer_to_tier(layer_name)

    def log_context_assembly_snapshot(
        self,
        request_id: str,
        user_id: Optional[str],
        conversation_id: Optional[str],
        context_assembly: Dict[str, Any],
    ) -> None:
        self._context_snapshot_facet.log_context_assembly_snapshot(
            request_id=request_id,
            user_id=user_id,
            conversation_id=conversation_id,
            context_assembly=context_assembly,
        )

    def get_memory_debug_info(self, user_id: str) -> Dict[str, Any]:
        return self._dashboard_facet.get_memory_debug_info(user_id=user_id)

    def get_retrieval_trace(self, request_id: str) -> Dict[str, Any]:
        return self._dashboard_facet.get_retrieval_trace(request_id=request_id)

    def get_write_decisions(self, conversation_id: str) -> Dict[str, Any]:
        return self._dashboard_facet.get_write_decisions(conversation_id=conversation_id)

    def get_context_snapshot(self, request_id: str) -> Dict[str, Any]:
        return self._dashboard_facet.get_context_snapshot(request_id=request_id)

    def get_critical_metrics(self) -> Dict[str, Any]:
        return self._dashboard_facet.get_critical_metrics()

    def check_alerts(self) -> List[Dict[str, Any]]:
        return self._dashboard_facet.check_alerts()

    def export_observability_data(self) -> Dict[str, Any]:
        return self._dashboard_facet.export_observability_data()

    def _redact_content(self, content: str) -> str:
        return redact_content(content)


def _compute_hash(text: str) -> str:
    return compute_hash(text)


observability_service = ObservabilityService()
