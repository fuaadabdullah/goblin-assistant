from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


def calculate_tier_breakdown(items: List[Any]) -> Dict[str, Dict[str, Any]]:
    tier_stats: Dict[str, Dict[str, Any]] = {}
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

    for stats in tier_stats.values():
        if stats["count"] > 0:
            stats["avg_relevance"] = round(stats["avg_relevance"] / stats["count"], 3)

    return tier_stats


def identify_truncations(items: List[Any], token_budget: int) -> List[Dict[str, Any]]:
    truncations: List[Dict[str, Any]] = []
    for item in items:
        if item.truncated:
            truncations.append(
                {
                    "source": item.source,
                    "source_id": item.source_id,
                    "original_tokens": item.token_count + 100,
                    "truncated_tokens": item.token_count,
                    "reason": "token_budget_exceeded",
                }
            )

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


def filter_traces(
    trace_cache: Dict[str, Any],
    *,
    user_id: Optional[str] = None,
    model: Optional[str] = None,
    time_window_hours: Optional[int] = None,
) -> List[Any]:
    cutoff_time = None
    if time_window_hours is not None:
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)

    traces = []
    for trace in trace_cache.values():
        if cutoff_time is not None and trace.timestamp < cutoff_time:
            continue
        if user_id and trace.user_id != user_id:
            continue
        if model and trace.model_selected != model:
            continue
        traces.append(trace)
    return traces


def traces_to_history(traces: List[Any], limit: int) -> List[Dict[str, Any]]:
    history = [trace.to_dict() for trace in traces]
    history.sort(key=lambda x: x["timestamp"], reverse=True)
    return history[:limit]


def build_retrieval_stats(
    relevant_traces: List[Any],
    *,
    user_id: Optional[str],
    time_window_hours: int,
    model: Optional[str],
) -> Dict[str, Any]:
    if not relevant_traces:
        return {
            "total_retrievals": 0,
            "time_window_hours": time_window_hours,
            "user_id": user_id,
            "model": model,
        }

    total = len(relevant_traces)
    token_usage = {
        "avg_tokens_used": round(sum(t.total_tokens_used for t in relevant_traces) / total, 2),
        "max_tokens_used": max(t.total_tokens_used for t in relevant_traces),
        "min_tokens_used": min(t.total_tokens_used for t in relevant_traces),
        "avg_token_utilization": round(
            sum(t.total_tokens_used / t.token_budget * 100 for t in relevant_traces) / total,
            2,
        ),
    }
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

    tier_distribution: Dict[str, int] = {}
    for trace in relevant_traces:
        for tier, stats in trace.tier_breakdown.items():
            tier_distribution[tier] = tier_distribution.get(tier, 0) + stats["count"]

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


def generate_quality_recommendations(
    avg_utilization: float,
    avg_relevance: float,
    truncation_rate: float,
    tier_effectiveness: Dict[str, Any],
) -> List[str]:
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
        recommendations.append("High truncation rate - review token allocation strategy")
    if avg_relevance < 0.5:
        recommendations.append(
            "Low relevance scores - review embedding quality and retrieval algorithms"
        )
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


def build_retrieval_quality_report(
    user_traces: List[Any],
    *,
    user_id: Optional[str],
) -> Dict[str, Any]:
    if not user_traces:
        return {
            "user_id": user_id,
            "status": "no_data",
            "message": "No retrieval traces found",
        }

    total_traces = len(user_traces)
    token_utilization = [t.total_tokens_used / t.token_budget * 100 for t in user_traces]
    avg_utilization = sum(token_utilization) / len(token_utilization)

    avg_relevance_scores = []
    for trace in user_traces:
        if trace.items_retrieved:
            avg_relevance_scores.append(
                sum(item.relevance_score for item in trace.items_retrieved)
                / len(trace.items_retrieved)
            )
    avg_relevance = (
        sum(avg_relevance_scores) / len(avg_relevance_scores) if avg_relevance_scores else 0
    )

    total_items = sum(len(t.items_retrieved) for t in user_traces)
    truncated_items = sum(
        sum(1 for item in t.items_retrieved if item.truncated) for t in user_traces
    )
    truncation_rate = truncated_items / max(1, total_items) * 100

    tier_effectiveness: Dict[str, Dict[str, Any]] = {}
    for trace in user_traces:
        for tier, stats in trace.tier_breakdown.items():
            if tier not in tier_effectiveness:
                tier_effectiveness[tier] = {
                    "total_items": 0,
                    "total_relevance": 0,
                    "count": 0,
                }
            tier_effectiveness[tier]["total_items"] += stats["count"]
            tier_effectiveness[tier]["total_relevance"] += stats["avg_relevance"] * stats["count"]
            tier_effectiveness[tier]["count"] += 1

    for eff in tier_effectiveness.values():
        eff["avg_relevance"] = eff["total_relevance"] / max(1, eff["total_items"])
        eff["usage_frequency"] = eff["count"] / total_traces * 100

    if avg_utilization < 30:
        quality_status = "poor"
    elif avg_utilization > 90 or truncation_rate > 20:
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
        "recommendations": generate_quality_recommendations(
            avg_utilization, avg_relevance, truncation_rate, tier_effectiveness
        ),
    }


def search_traces(
    trace_cache: Dict[str, Any],
    *,
    query: str,
    user_id: Optional[str] = None,
    model: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    min_relevance: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> List[Dict[str, Any]]:
    results = []
    for trace in trace_cache.values():
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
