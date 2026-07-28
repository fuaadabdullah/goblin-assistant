from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


def filter_snapshots(
    snapshot_cache: Dict[str, Any],
    *,
    user_id: Optional[str] = None,
    model: Optional[str] = None,
    time_window_hours: Optional[int] = None,
) -> List[Any]:
    cutoff_time = None
    if time_window_hours is not None:
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)

    snapshots = []
    for snapshot in snapshot_cache.values():
        if cutoff_time is not None and snapshot.timestamp < cutoff_time:
            continue
        if user_id and snapshot.user_id != user_id:
            continue
        if model and snapshot.model_target != model:
            continue
        snapshots.append(snapshot)
    return snapshots


def snapshots_to_history(snapshots: List[Any], limit: int) -> List[Dict[str, Any]]:
    history = [snapshot.to_dict() for snapshot in snapshots]
    history.sort(key=lambda x: x["timestamp"], reverse=True)
    return history[:limit]


def get_layer_type_distribution(snapshots: List[Any]) -> Dict[str, int]:
    layer_types: Dict[str, int] = {}
    for snapshot in snapshots:
        for layer in snapshot.context_layers:
            layer_type = layer.get("name", "unknown")
            layer_types[layer_type] = layer_types.get(layer_type, 0) + 1
    return layer_types


def build_context_assembly_stats(
    relevant_snapshots: List[Any],
    *,
    user_id: Optional[str],
    time_window_hours: int,
    model: Optional[str],
) -> Dict[str, Any]:
    if not relevant_snapshots:
        return {
            "total_assemblies": 0,
            "time_window_hours": time_window_hours,
            "user_id": user_id,
            "model": model,
        }

    total = len(relevant_snapshots)
    token_stats = {
        "avg_tokens_used": round(sum(s.total_tokens for s in relevant_snapshots) / total, 2),
        "max_tokens_used": max(s.total_tokens for s in relevant_snapshots),
        "min_tokens_used": min(s.total_tokens for s in relevant_snapshots),
        "avg_token_utilization": round(
            sum(s.total_tokens / s.token_budget * 100 for s in relevant_snapshots) / total,
            2,
        ),
    }
    assembly_stats = {
        "avg_assembly_time": round(sum(s.assembly_time_ms for s in relevant_snapshots) / total, 2),
        "max_assembly_time": max(s.assembly_time_ms for s in relevant_snapshots),
        "min_assembly_time": min(s.assembly_time_ms for s in relevant_snapshots),
    }
    redaction_stats = {
        "total_redactions": sum(
            s.redaction_details.get("items_redacted", 0) for s in relevant_snapshots
        ),
        "snapshots_with_redaction": sum(
            1 for s in relevant_snapshots if s.redaction_details.get("items_redacted", 0) > 0
        ),
        "redaction_rate": round(
            sum(1 for s in relevant_snapshots if s.redaction_details.get("items_redacted", 0) > 0)
            / total
            * 100,
            2,
        ),
    }
    layer_stats = {
        "avg_layers_per_assembly": round(
            sum(len(s.context_layers) for s in relevant_snapshots) / total, 2
        ),
        "layer_types": get_layer_type_distribution(relevant_snapshots),
    }
    error_count = sum(1 for s in relevant_snapshots if s.error)
    error_rate = round(error_count / total * 100, 2)
    return {
        "total_assemblies": total,
        "time_window_hours": time_window_hours,
        "user_id": user_id,
        "model": model,
        "token_stats": token_stats,
        "assembly_stats": assembly_stats,
        "redaction_stats": redaction_stats,
        "layer_stats": layer_stats,
        "error_rate": error_rate,
    }


def generate_health_recommendations(
    avg_utilization: float,
    avg_assembly_time: float,
    redaction_rate: float,
    error_rate: float,
    layer_consistency: float,
) -> List[str]:
    recommendations = []
    if avg_utilization > 95:
        recommendations.append("High token utilization - consider increasing token budget")
    if avg_assembly_time > 1000:
        recommendations.append("Slow context assembly - review layer processing efficiency")
    if redaction_rate > 20:
        recommendations.append("High redaction rate - review data filtering before assembly")
    if error_rate > 5:
        recommendations.append("High error rate - review context assembly logic")
    if layer_consistency < 70:
        recommendations.append("Inconsistent layer assembly - review layer ordering logic")
    if not recommendations:
        recommendations.append("Context assembly health looks good - continue monitoring")
    return recommendations


def build_context_health_report(
    user_snapshots: List[Any],
    *,
    user_id: Optional[str],
) -> Dict[str, Any]:
    if not user_snapshots:
        return {
            "user_id": user_id,
            "status": "no_data",
            "message": "No context snapshots found",
        }

    total_snapshots = len(user_snapshots)
    token_utilization = [s.total_tokens / s.token_budget * 100 for s in user_snapshots]
    avg_utilization = sum(token_utilization) / len(token_utilization)
    assembly_times = [s.assembly_time_ms for s in user_snapshots]
    avg_assembly_time = sum(assembly_times) / len(assembly_times)
    total_redactions = sum(s.redaction_details.get("items_redacted", 0) for s in user_snapshots)
    redaction_rate = (
        total_redactions / max(1, sum(len(s.context_layers) for s in user_snapshots)) * 100
    )
    error_count = sum(1 for s in user_snapshots if s.error)
    error_rate = error_count / total_snapshots * 100
    layer_counts = [len(s.context_layers) for s in user_snapshots]
    layer_consistency = (
        100 - (max(layer_counts) - min(layer_counts)) / max(1, sum(layer_counts)) * 100
    )

    if error_rate > 10:
        health_status = "critical"
    elif (
        avg_assembly_time > 1000
        or avg_utilization > 95
        or redaction_rate > 20
        or layer_consistency < 70
    ):
        health_status = "warning"
    else:
        health_status = "healthy"

    return {
        "user_id": user_id,
        "health_status": health_status,
        "metrics": {
            "total_assemblies": total_snapshots,
            "avg_token_utilization": round(avg_utilization, 2),
            "avg_assembly_time_ms": round(avg_assembly_time, 2),
            "redaction_rate": round(redaction_rate, 2),
            "error_rate": round(error_rate, 2),
            "layer_consistency": round(layer_consistency, 2),
            "assembly_performance": {
                "min_time_ms": min(assembly_times),
                "max_time_ms": max(assembly_times),
                "p95_time_ms": sorted(assembly_times)[int(0.95 * len(assembly_times))]
                if assembly_times
                else 0,
            },
        },
        "recommendations": generate_health_recommendations(
            avg_utilization,
            avg_assembly_time,
            redaction_rate,
            error_rate,
            layer_consistency,
        ),
    }


def search_snapshot_cache(
    snapshot_cache: Dict[str, Any],
    *,
    query: str,
    user_id: Optional[str] = None,
    model: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    min_tokens: Optional[int] = None,
    max_tokens: Optional[int] = None,
) -> List[Dict[str, Any]]:
    results = []
    for snapshot in snapshot_cache.values():
        if user_id and snapshot.user_id != user_id:
            continue
        if model and snapshot.model_target != model:
            continue
        if start_time and snapshot.timestamp < start_time:
            continue
        if end_time and snapshot.timestamp > end_time:
            continue
        if min_tokens and snapshot.total_tokens < min_tokens:
            continue
        if max_tokens and snapshot.total_tokens > max_tokens:
            continue
        if query:
            snapshot_text = " ".join(layer.get("content", "") for layer in snapshot.context_layers)
            if query.lower() not in snapshot_text.lower():
                continue
        results.append(snapshot.to_dict())
    results.sort(key=lambda x: x["timestamp"], reverse=True)
    return results


def build_replay_context(snapshot: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    return {
        "request_id": request_id,
        "context_hash": snapshot["context_hash"],
        "reconstructed_context": "\n\n".join(
            f"[{layer.get('name', 'LAYER')}] {layer.get('content', '')}"
            for layer in snapshot["context_layers"]
        ),
        "token_usage": {
            "total": snapshot["total_tokens"],
            "remaining": snapshot["remaining_tokens"],
            "budget": snapshot["token_budget"],
        },
        "assembly_details": {
            "layers": len(snapshot["context_layers"]),
            "assembly_time": snapshot["assembly_time_ms"],
            "model_target": snapshot["model_target"],
        },
        "redaction_details": snapshot["redaction_details"],
    }
