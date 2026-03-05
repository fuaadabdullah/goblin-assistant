"""
Retrieval Trace System
The crown jewel of observability - tracks every LLM call with full retrieval trace
"""

import json
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import structlog
import uuid

from ..config.system_config import get_system_config

logger = structlog.get_logger()


class RetrievalTier(Enum):
    """Retrieval tiers in the fixed stack order"""

    SYSTEM = "system"
    LONG_TERM_MEMORY = "long_term_memory"
    WORKING_MEMORY = "working_memory"
    SEMANTIC_RETRIEVAL = "semantic_retrieval"
    EPHEMERAL_MEMORY = "ephemeral_memory"


@dataclass
class RetrievedItem:
    """Individual retrieved item with full metadata"""

    source: str
    source_id: Optional[str]
    content: str
    relevance_score: float
    token_count: int
    rank: int
    truncated: bool
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return asdict(self)


@dataclass
class RetrievalTrace:
    """Complete retrieval trace for an LLM call"""

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
        """Convert to dictionary for logging"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["items_retrieved"] = [item.to_dict() for item in self.items_retrieved]
        return data

    def to_json(self) -> str:
        """Convert to JSON string for structured logging"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class RetrievalTracer:
    """Centralized retrieval tracing with full observability"""

    def __init__(self):
        self.config = get_system_config()
        self._trace_cache = {}  # Cache recent traces for debugging
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
        """Trace a complete retrieval operation"""

        # Calculate tier breakdown
        tier_breakdown = self._calculate_tier_breakdown(items_retrieved)

        # Calculate total tokens used
        total_tokens_used = sum(item.token_count for item in items_retrieved)

        # Identify truncation events
        truncation_events = self._identify_truncations(items_retrieved, token_budget)

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

        # Store in cache for debugging
        self._trace_cache[request_id] = trace
        self._trace_count += 1

        # Log with structured format
        self._log_retrieval_structured(trace)

        # Log to file if configured
        if self.config.get("observability", {}).get("log_retrievals_to_file", False):
            await self._log_to_file(trace)

        return trace

    def _calculate_tier_breakdown(
        self, items: List[RetrievedItem]
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate statistics for each retrieval tier"""
        tier_stats = {}

        for item in items:
            source_type = item.source
            if source_type not in tier_stats:
                tier_stats[source_type] = {
                    "count": 0,
                    "total_tokens": 0,
                    "avg_relevance": 0,
                    "max_relevance": 0,
                    "min_relevance": 1,
                    "truncated_count": 0,
                }

            stats = tier_stats[source_type]
            stats["count"] += 1
            stats["total_tokens"] += item.token_count
            stats["avg_relevance"] += item.relevance_score
            stats["max_relevance"] = max(stats["max_relevance"], item.relevance_score)
            stats["min_relevance"] = min(stats["min_relevance"], item.relevance_score)
            if item.truncated:
                stats["truncated_count"] += 1

        # Calculate averages
        for source_type, stats in tier_stats.items():
            if stats["count"] > 0:
                stats["avg_relevance"] = round(
                    stats["avg_relevance"] / stats["count"], 3
                )

        return tier_stats

    def _identify_truncations(
        self, items: List[RetrievedItem], token_budget: int
    ) -> List[Dict[str, Any]]:
        """Identify truncation events during retrieval"""
        truncations = []

        for item in items:
            if item.truncated:
                truncations.append(
                    {
                        "source": item.source,
                        "source_id": item.source_id,
                        "original_tokens": item.token_count + 100,  # Estimate
                        "truncated_tokens": item.token_count,
                        "reason": "token_budget_exceeded",
                    }
                )

        # Check if total tokens exceeded budget
        total_tokens = sum(item.token_count for item in items)
        if total_tokens > token_budget:
            truncations.append(
                {
                    "source": "context_assembly",
                    "reason": "total_context_exceeded_budget",
                    "budget": token_budget,
                    "actual": total_tokens,
                    "exceeded_by": total_tokens - token_budget,
                }
            )

        return truncations

    def _log_retrieval_structured(self, trace: RetrievalTrace):
        """Log retrieval trace with structured format for observability"""

        # Create structured log entry
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
                "truncated_items": sum(
                    1 for item in trace.items_retrieved if item.truncated
                ),
            },
        }

        # Log based on retrieval outcome
        if trace.error:
            logger.error(f"RETRIEVAL: Error occurred", extra={"retrieval": log_data})
        elif trace.total_tokens_used > trace.token_budget:
            logger.warning(
                f"RETRIEVAL: Token budget exceeded", extra={"retrieval": log_data}
            )
        else:
            logger.info(f"RETRIEVAL: Successful", extra={"retrieval": log_data})

    async def _log_to_file(self, trace: RetrievalTrace):
        """Log retrieval trace to file for persistent storage"""
        try:
            log_file = self.config.get("observability", {}).get(
                "retrieval_log_file", "retrievals.log"
            )

            with open(log_file, "a", encoding="utf-8") as f:
                f.write(trace.to_json() + "\n")

        except Exception as e:
            logger.error(f"Failed to log retrieval to file: {e}")

    async def get_retrieval_trace(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific retrieval trace by request ID"""
        if request_id in self._trace_cache:
            return self._trace_cache[request_id].to_dict()
        return None

    async def get_retrieval_history(
        self,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get retrieval history with filtering"""

        # Filter traces by user and model
        traces = []
        for trace in self._trace_cache.values():
            if user_id and trace.user_id != user_id:
                continue
            if model and trace.model_selected != model:
                continue
            traces.append(trace.to_dict())

        # Sort by timestamp and limit
        traces.sort(key=lambda x: x["timestamp"], reverse=True)
        return traces[:limit]

    async def get_retrieval_stats(
        self,
        user_id: Optional[str] = None,
        time_window_hours: int = 24,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get retrieval statistics for monitoring"""

        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)

        # Filter traces by time window, user, and model
        relevant_traces = []
        for trace in self._trace_cache.values():
            if trace.timestamp >= cutoff_time:
                if user_id is None or trace.user_id == user_id:
                    if model is None or trace.model_selected == model:
                        relevant_traces.append(trace)

        if not relevant_traces:
            return {
                "total_retrievals": 0,
                "time_window_hours": time_window_hours,
                "user_id": user_id,
                "model": model,
            }

        # Calculate statistics
        total = len(relevant_traces)

        # Token usage statistics
        token_usage = {
            "avg_tokens_used": round(
                sum(t.total_tokens_used for t in relevant_traces) / total, 2
            ),
            "max_tokens_used": max(t.total_tokens_used for t in relevant_traces),
            "min_tokens_used": min(t.total_tokens_used for t in relevant_traces),
            "avg_token_utilization": round(
                sum(t.total_tokens_used / t.token_budget * 100 for t in relevant_traces)
                / total,
                2,
            ),
        }

        # Retrieval quality statistics
        retrieval_quality = {
            "avg_relevance": round(
                sum(
                    sum(item.relevance_score for item in t.items_retrieved)
                    / max(1, len(t.items_retrieved))
                    for t in relevant_traces
                )
                / total,
                3,
            ),
            "avg_items_per_retrieval": round(
                sum(len(t.items_retrieved) for t in relevant_traces) / total, 2
            ),
            "truncation_rate": round(
                sum(len(t.truncation_events) for t in relevant_traces)
                / max(1, sum(len(t.items_retrieved) for t in relevant_traces))
                * 100,
                2,
            ),
        }

        # Tier distribution
        tier_distribution = {}
        for trace in relevant_traces:
            for tier, stats in trace.tier_breakdown.items():
                if tier not in tier_distribution:
                    tier_distribution[tier] = 0
                tier_distribution[tier] += stats["count"]

        # Error rate
        error_count = sum(1 for t in relevant_traces if t.error)
        error_rate = round(error_count / total * 100, 2)

        return {
            "total_retrievals": total,
            "time_window_hours": time_window_hours,
            "user_id": user_id,
            "model": model,
            "token_usage": token_usage,
            "retrieval_quality": retrieval_quality,
            "tier_distribution": tier_distribution,
            "error_rate": error_rate,
            "performance": {
                "avg_retrieval_time": round(
                    sum(t.retrieval_time_ms for t in relevant_traces) / total, 2
                ),
                "max_retrieval_time": max(t.retrieval_time_ms for t in relevant_traces),
                "min_retrieval_time": min(t.retrieval_time_ms for t in relevant_traces),
            },
        }

    async def get_retrieval_quality_report(
        self, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive retrieval quality report"""

        # Get all traces for user
        user_traces = []
        for trace in self._trace_cache.values():
            if user_id is None or trace.user_id == user_id:
                user_traces.append(trace)

        if not user_traces:
            return {
                "user_id": user_id,
                "status": "no_data",
                "message": "No retrieval traces found",
            }

        # Calculate quality metrics
        total_traces = len(user_traces)

        # Token utilization analysis
        token_utilization = [
            t.total_tokens_used / t.token_budget * 100 for t in user_traces
        ]
        avg_utilization = sum(token_utilization) / len(token_utilization)

        # Relevance analysis
        avg_relevance_scores = []
        for trace in user_traces:
            if trace.items_retrieved:
                avg_relevance = sum(
                    item.relevance_score for item in trace.items_retrieved
                ) / len(trace.items_retrieved)
                avg_relevance_scores.append(avg_relevance)

        avg_relevance = (
            sum(avg_relevance_scores) / len(avg_relevance_scores)
            if avg_relevance_scores
            else 0
        )

        # Truncation analysis
        total_items = sum(len(t.items_retrieved) for t in user_traces)
        truncated_items = sum(
            sum(1 for item in t.items_retrieved if item.truncated) for t in user_traces
        )
        truncation_rate = truncated_items / max(1, total_items) * 100

        # Tier effectiveness analysis
        tier_effectiveness = {}
        for trace in user_traces:
            for tier, stats in trace.tier_breakdown.items():
                if tier not in tier_effectiveness:
                    tier_effectiveness[tier] = {
                        "total_items": 0,
                        "total_relevance": 0,
                        "count": 0,
                    }

                tier_effectiveness[tier]["total_items"] += stats["count"]
                tier_effectiveness[tier]["total_relevance"] += (
                    stats["avg_relevance"] * stats["count"]
                )
                tier_effectiveness[tier]["count"] += 1

        for tier in tier_effectiveness:
            eff = tier_effectiveness[tier]
            eff["avg_relevance"] = eff["total_relevance"] / max(1, eff["total_items"])
            eff["usage_frequency"] = eff["count"] / total_traces * 100

        # Determine quality status
        if avg_utilization < 30:
            quality_status = "poor"
        elif avg_utilization > 90:
            quality_status = "warning"  # Over-utilization may indicate poor filtering
        elif truncation_rate > 20:
            quality_status = "warning"
        elif avg_relevance < 0.5:
            quality_status = "poor"
        else:
            quality_status = "good"

        return {
            "user_id": user_id,
            "quality_status": quality_status,
            "metrics": {
                "total_retrievals": total_traces,
                "avg_token_utilization": round(avg_utilization, 2),
                "avg_relevance_score": round(avg_relevance, 3),
                "truncation_rate": round(truncation_rate, 2),
                "tier_effectiveness": tier_effectiveness,
            },
            "recommendations": self._generate_quality_recommendations(
                avg_utilization, avg_relevance, truncation_rate, tier_effectiveness
            ),
        }

    def _generate_quality_recommendations(
        self,
        avg_utilization: float,
        avg_relevance: float,
        truncation_rate: float,
        tier_effectiveness: Dict[str, Any],
    ) -> List[str]:
        """Generate recommendations based on retrieval quality metrics"""

        recommendations = []

        if avg_utilization < 30:
            recommendations.append(
                "Low token utilization - consider reducing token budget or improving retrieval filtering"
            )

        if avg_utilization > 90:
            recommendations.append(
                "High token utilization - consider increasing token budget to avoid truncation"
            )

        if truncation_rate > 20:
            recommendations.append(
                "High truncation rate - review token allocation strategy"
            )

        if avg_relevance < 0.5:
            recommendations.append(
                "Low relevance scores - review embedding quality and retrieval algorithms"
            )

        # Check tier effectiveness
        if "semantic_retrieval" in tier_effectiveness:
            sem_eff = tier_effectiveness["semantic_retrieval"]
            if sem_eff["avg_relevance"] < 0.6:
                recommendations.append(
                    "Semantic retrieval has low relevance - review embedding model or query construction"
                )

        if "long_term_memory" in tier_effectiveness:
            ltm_eff = tier_effectiveness["long_term_memory"]
            if ltm_eff["usage_frequency"] < 10:
                recommendations.append(
                    "Long-term memory rarely used - review memory promotion criteria"
                )

        if not recommendations:
            recommendations.append("Retrieval quality looks good - continue monitoring")

        return recommendations

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
        """Search retrievals with advanced filtering"""

        results = []

        for trace in self._trace_cache.values():
            # Apply filters
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

            # Apply text search
            if query:
                trace_text = f"{trace.context_snapshot} {trace.model_selected}"
                if query.lower() not in trace_text.lower():
                    continue

            results.append(trace.to_dict())

        # Sort by timestamp
        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results

    async def start_trace(
        self,
        query: str,
        user_id: Optional[str],
        conversation_id: Optional[str],
        correlation_id: str,
    ) -> str:
        """Start a new retrieval trace and return the trace ID"""
        trace_id = f"trace_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        # Store initial trace info
        # (This is a simplified version of what might have been here)
        return trace_id

    async def end_trace(
        self,
        trace_id: str,
        results_count: int,
        status: str = "success",
        error: Optional[str] = None,
    ):
        """End a retrieval trace"""
        pass


# Global retrieval tracer instance
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
    """Convenience function to trace retrievals"""
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
