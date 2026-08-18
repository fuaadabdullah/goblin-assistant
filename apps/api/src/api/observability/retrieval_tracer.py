"""
Retrieval Trace System.

Compatibility facade over retrieval_tracer_helpers.
Preserves the historical dataclasses, singleton, and monkeypatchable methods.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

from ..config.system_config import get_system_config
from .retrieval_tracer_helpers import (
    build_retrieval_quality_report,
    build_retrieval_stats,
    calculate_tier_breakdown,
    filter_traces,
    generate_quality_recommendations,
    identify_truncations,
    traces_to_history,
)

logger = structlog.get_logger()


class RetrievalTier(Enum):
    """Retrieval tiers in the fixed stack order."""

    SYSTEM = "system"
    LONG_TERM_MEMORY = "long_term_memory"
    WORKING_MEMORY = "working_memory"
    SEMANTIC_RETRIEVAL = "semantic_retrieval"
    EPHEMERAL_MEMORY = "ephemeral_memory"


@dataclass
class RetrievedItem:
    """Individual retrieved item with full metadata."""

    source: str
    source_id: Optional[str]
    content: str
    relevance_score: float
    token_count: int
    rank: int
    truncated: bool
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievalTrace:
    """Complete retrieval trace for an LLM call."""

    request_id: str
    user_id: Optional[str]
    timestamp: datetime
    model_selected: str
    token_budget: int
    total_tokens_used: int
    items_retrieved: List[RetrievedItem]
    tier_breakdown: Dict[str, Dict[str, Any]]
    context_hash: str
    context_snapshot: str
    retrieval_time_ms: float
    truncation_events: List[Dict[str, Any]]
    error: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["items_retrieved"] = [item.to_dict() for item in self.items_retrieved]
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class RetrievalTracer:
    """Centralized retrieval tracing with full observability."""

    def __init__(self):
        self.config = get_system_config()
        self._trace_cache: Dict[str, RetrievalTrace] = {}
        self._trace_count = 0

    async def trace_retrieval(
        self,
        request_id: str,
        user_id: Optional[str],
        model_selected: str,
        token_budget: int,
        items_retrieved: List[RetrievedItem],
        context_hash: str,
        context_snapshot: str,
        retrieval_time_ms: float,
        error: Optional[str] = None,
    ) -> RetrievalTrace:
        tier_breakdown = calculate_tier_breakdown(items_retrieved)
        total_tokens_used = sum(item.token_count for item in items_retrieved)
        truncation_events = identify_truncations(items_retrieved, token_budget)

        trace = RetrievalTrace(
            request_id=request_id,
            user_id=user_id,
            timestamp=datetime.utcnow(),
            model_selected=model_selected,
            token_budget=token_budget,
            total_tokens_used=total_tokens_used,
            items_retrieved=items_retrieved,
            tier_breakdown=tier_breakdown,
            context_hash=context_hash,
            context_snapshot=context_snapshot,
            retrieval_time_ms=retrieval_time_ms,
            truncation_events=truncation_events,
            error=error,
        )

        self._trace_cache[request_id] = trace
        self._trace_count += 1
        self._log_retrieval_structured(trace)

        if self.config.get("observability", {}).get("log_retrievals_to_file", False):
            await self._log_to_file(trace)

        return trace

    def _calculate_tier_breakdown(self, items: List[RetrievedItem]) -> Dict[str, Dict[str, Any]]:
        return calculate_tier_breakdown(items)

    def _identify_truncations(
        self, items: List[RetrievedItem], token_budget: int
    ) -> List[Dict[str, Any]]:
        return identify_truncations(items, token_budget)

    def _log_retrieval_structured(self, trace: RetrievalTrace):
        log_data = {
            "observability_event": True,
            "event_type": "retrieval_trace",
            "retrieval": {
                "request_id": trace.request_id,
                "user_id": trace.user_id,
                "model": trace.model_selected,
                "token_budget": trace.token_budget,
                "total_tokens_used": trace.total_tokens_used,
                "retrieval_time_ms": trace.retrieval_time_ms,
                "context_hash": trace.context_hash,
                "error": trace.error,
            },
            "tier_breakdown": trace.tier_breakdown,
            "truncations": trace.truncation_events,
            "items_summary": {
                "total_items": len(trace.items_retrieved),
                "avg_relevance": round(
                    sum(item.relevance_score for item in trace.items_retrieved)
                    / max(1, len(trace.items_retrieved)),
                    3,
                ),
                "max_relevance": max(
                    (item.relevance_score for item in trace.items_retrieved), default=0
                ),
                "min_relevance": min(
                    (item.relevance_score for item in trace.items_retrieved), default=0
                ),
                "truncated_items": sum(1 for item in trace.items_retrieved if item.truncated),
            },
        }

        if trace.error:
            logger.error("RETRIEVAL: Error occurred", extra={"retrieval": log_data})
        elif trace.total_tokens_used > trace.token_budget:
            logger.warning("RETRIEVAL: Token budget exceeded", extra={"retrieval": log_data})
        else:
            logger.info("RETRIEVAL: Successful", extra={"retrieval": log_data})

    async def _log_to_file(self, trace: RetrievalTrace):
        try:
            log_file = self.config.get("observability", {}).get(
                "retrieval_log_file", "retrievals.log"
            )

            def _append() -> None:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(trace.to_json() + "\n")

            await asyncio.to_thread(_append)
        except Exception as e:
            logger.error("Failed to log retrieval to file:", error=str(e))

    async def get_retrieval_trace(self, request_id: str) -> Optional[Dict[str, Any]]:
        if request_id in self._trace_cache:
            return self._trace_cache[request_id].to_dict()
        return None

    async def get_retrieval_history(
        self,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        traces = filter_traces(self._trace_cache, user_id=user_id, model=model)
        return traces_to_history(traces, limit)

    async def get_retrieval_stats(
        self,
        user_id: Optional[str] = None,
        time_window_hours: int = 24,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        relevant_traces = filter_traces(
            self._trace_cache,
            user_id=user_id,
            model=model,
            time_window_hours=time_window_hours,
        )
        return build_retrieval_stats(
            relevant_traces,
            user_id=user_id,
            time_window_hours=time_window_hours,
            model=model,
        )

    async def get_retrieval_quality_report(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        user_traces = filter_traces(self._trace_cache, user_id=user_id)
        return build_retrieval_quality_report(user_traces, user_id=user_id)

    def _generate_quality_recommendations(
        self,
        avg_utilization: float,
        avg_relevance: float,
        truncation_rate: float,
        tier_effectiveness: Dict[str, Any],
    ) -> List[str]:
        return generate_quality_recommendations(
            avg_utilization, avg_relevance, truncation_rate, tier_effectiveness
        )

    async def search_retrievals(
        self,
        query: str,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        min_relevance: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        results = []

        for trace in self._trace_cache.values():
            if user_id and trace.user_id != user_id:
                continue
            if model and trace.model_selected != model:
                continue
            if start_time and trace.timestamp < start_time:
                continue
            if end_time and trace.timestamp > end_time:
                continue
            if min_relevance and any(
                item.relevance_score < min_relevance for item in trace.items_retrieved
            ):
                continue
            if max_tokens and trace.total_tokens_used > max_tokens:
                continue
            if query:
                trace_text = f"{trace.context_snapshot} {trace.model_selected}"
                if query.lower() not in trace_text.lower():
                    continue
            results.append(trace.to_dict())

        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results

    async def start_trace(
        self,
        query: str,
        user_id: Optional[str],
        conversation_id: Optional[str],
        correlation_id: str,
    ) -> str:
        trace_id = f"trace_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        return trace_id

    async def end_trace(
        self,
        trace_id: str,
        results_count: int,
        status: str = "success",
        error: Optional[str] = None,
    ):
        return None

    async def record_tier_breakdown(
        self,
        trace_id: str,
        tier: str,
        results: List[Any],
        total_results: int,
    ) -> None:
        logger.debug(
            "retrieval_tier_breakdown",
            trace_id=trace_id,
            tier=tier,
            total_results=total_results,
            result_count=len(results) if results else 0,
        )


retrieval_tracer = RetrievalTracer()


async def trace_retrieval(
    request_id: str,
    user_id: Optional[str],
    model_selected: str,
    token_budget: int,
    items_retrieved: List[RetrievedItem],
    context_hash: str,
    context_snapshot: str,
    retrieval_time_ms: float,
    error: Optional[str] = None,
) -> RetrievalTrace:
    return await retrieval_tracer.trace_retrieval(
        request_id=request_id,
        user_id=user_id,
        model_selected=model_selected,
        token_budget=token_budget,
        items_retrieved=items_retrieved,
        context_hash=context_hash,
        context_snapshot=context_snapshot,
        retrieval_time_ms=retrieval_time_ms,
        error=error,
    )
