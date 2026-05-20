"""
Operations and monitoring endpoints for admin UI
Aggregates existing metrics and provides frontend-friendly JSON responses
Enhanced with advanced aggregation, security controls, and trend analysis
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from datetime import datetime, timedelta
import asyncio
import time
import statistics
import os
from collections import defaultdict

from .health import (
    health_check,
    _check_chroma,
    _check_mcp,
    _check_raptor,
    _check_sandbox,
    _check_cost_tracking,
)
from .monitoring import monitor
from .storage.cache import cache
from .storage.tasks import task_store
from .config.redis_config import redis_config
from .ops.aggregator import aggregator
from .ops.security import (
    require_ops_access,
    require_ops_write_access,
    require_ops_reset_access,
    get_ops_audit_log,
    get_security_summary,
)
from .ops.audit import (
    audit_logger,
    AuditEventType,
    AuditSeverity,
    log_ops_event,
    get_audit_summary,
)

router = APIRouter(prefix="/ops", tags=["operations"])


# Circuit breaker state tracking
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        elif self.state == "HALF_OPEN":
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time,
            "time_until_recovery": max(
                0, self.recovery_timeout - (time.time() - self.last_failure_time)
            )
            if self.state == "OPEN"
            else 0,
        }


# Global circuit breaker instances per provider
circuit_breakers: Dict[str, CircuitBreaker] = {}


class PerformanceMetrics:
    def __init__(self):
        self.response_times: Dict[str, List[float]] = defaultdict(list)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.total_requests: Dict[str, int] = defaultdict(int)
        self.start_time = time.time()

    def record_request(self, provider: str, response_time: float, success: bool):
        self.total_requests[provider] += 1
        self.response_times[provider].append(response_time)

        if len(self.response_times[provider]) > 100:  # Keep last 100 measurements
            self.response_times[provider] = self.response_times[provider][-100:]

        if not success:
            self.error_counts[provider] += 1

    def get_metrics(self, provider: str) -> Dict[str, Any]:
        times = self.response_times[provider]
        total = self.total_requests[provider]
        errors = self.error_counts[provider]

        if not times:
            return {
                "avg_response_time": 0,
                "min_response_time": 0,
                "max_response_time": 0,
                "p95_response_time": 0,
                "error_rate": 0,
                "total_requests": total,
                "error_count": errors,
            }

        return {
            "avg_response_time": round(statistics.mean(times), 2),
            "min_response_time": round(min(times), 2),
            "max_response_time": round(max(times), 2),
            "p95_response_time": round(statistics.quantiles(times, n=20)[-1], 2)
            if len(times) > 20
            else round(max(times), 2),
            "error_rate": round((errors / total * 100) if total > 0 else 0, 2),
            "total_requests": total,
            "error_count": errors,
        }


# Global performance metrics instance
performance_metrics = PerformanceMetrics()


@router.get("/health/summary")
async def health_summary() -> Dict[str, Any]:
    """Comprehensive system health overview for admin dashboard"""
    try:
        # Get base health check
        base_health = await health_check()

        # Get extended health checks
        chroma_health = await _check_chroma()
        mcp_health = await _check_mcp()
        raptor_health = await _check_raptor()
        sandbox_health = await _check_sandbox()
        cost_health = await _check_cost_tracking()

        # Calculate overall status
        component_statuses = [
            base_health["status"],
            chroma_health["status"],
            mcp_health["status"],
            raptor_health["status"],
            sandbox_health["status"],
        ]

        overall_status = (
            "healthy"
            if all(status == "healthy" for status in component_statuses)
            else "degraded"
            if "degraded" in component_statuses
            else "warnings"
        )

        # Calculate uptime
        uptime_seconds = time.time() - performance_metrics.start_time
        uptime_days = int(uptime_seconds // 86400)
        uptime_hours = int((uptime_seconds % 86400) // 3600)
        uptime_minutes = int((uptime_seconds % 3600) // 60)

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": {
                "seconds": int(uptime_seconds),
                "formatted": f"{uptime_days}d {uptime_hours}h {uptime_minutes}m",
            },
            "components": {
                "api": base_health["components"]["api"],
                "routing": base_health["components"]["routing"],
                "database": base_health["components"]["database"],
                "redis": base_health["components"]["redis"],
                "providers": base_health["components"]["providers"],
                "security": base_health["components"]["security"],
                "chroma": chroma_health,
                "mcp": mcp_health,
                "raptor": raptor_health,
                "sandbox": sandbox_health,
                "cost_tracking": cost_health,
            },
            "summary": {
                "total_components": len(component_statuses),
                "healthy_components": len(
                    [s for s in component_statuses if s == "healthy"]
                ),
                "degraded_components": len(
                    [s for s in component_statuses if s == "degraded"]
                ),
                "warning_components": len(
                    [s for s in component_statuses if s == "warnings"]
                ),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health summary failed: {str(e)}")


@router.get("/providers/status")
async def providers_status() -> Dict[str, Any]:
    """Provider status matrix with performance metrics and circuit breaker states"""
    try:
        # Get provider status from monitor
        provider_status = await monitor.get_status()

        # Get provider settings for capabilities
        from .config.providers import get_provider_settings

        provider_settings = get_provider_settings()
        settings_map = {p["name"]: p for p in provider_settings}

        # Build enhanced provider status
        enhanced_status = {}

        for provider_name, status in provider_status.items():
            # Get or create circuit breaker for this provider
            if provider_name not in circuit_breakers:
                circuit_breakers[provider_name] = CircuitBreaker()

            cb = circuit_breakers[provider_name]

            # Get performance metrics
            metrics = performance_metrics.get_metrics(provider_name)

            # Get provider settings
            settings = settings_map.get(provider_name, {})

            enhanced_status[provider_name] = {
                "name": provider_name,
                "status": status.get("status", "unknown"),
                "last_check": status.get("last_check"),
                "latency_ms": status.get("latency_ms", 0),
                "error": status.get("error"),
                "capabilities": settings.get("capabilities", []),
                "models": settings.get("models", []),
                "priority_tier": settings.get("priority_tier", 0),
                "circuit_breaker": cb.get_status(),
                "performance": metrics,
                "health_score": _calculate_health_score(status, metrics, cb),
            }

        # Add any configured providers that aren't in status yet
        for provider_name, settings in settings_map.items():
            if provider_name not in enhanced_status:
                if provider_name not in circuit_breakers:
                    circuit_breakers[provider_name] = CircuitBreaker()

                cb = circuit_breakers[provider_name]
                metrics = performance_metrics.get_metrics(provider_name)

                enhanced_status[provider_name] = {
                    "name": provider_name,
                    "status": "unknown",
                    "last_check": None,
                    "latency_ms": 0,
                    "error": "Not yet checked",
                    "capabilities": settings.get("capabilities", []),
                    "models": settings.get("models", []),
                    "priority_tier": settings.get("priority_tier", 0),
                    "circuit_breaker": cb.get_status(),
                    "performance": metrics,
                    "health_score": 0,
                }

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "providers": enhanced_status,
            "summary": {
                "total_providers": len(enhanced_status),
                "healthy_providers": len(
                    [p for p in enhanced_status.values() if p["status"] == "healthy"]
                ),
                "unhealthy_providers": len(
                    [p for p in enhanced_status.values() if p["status"] != "healthy"]
                ),
                "open_circuit_breakers": len(
                    [
                        p
                        for p in enhanced_status.values()
                        if p["circuit_breaker"]["state"] == "OPEN"
                    ]
                ),
                "avg_latency": round(
                    statistics.mean(
                        [
                            p["latency_ms"]
                            for p in enhanced_status.values()
                            if p["latency_ms"] > 0
                        ]
                    )
                    if any(p["latency_ms"] > 0 for p in enhanced_status.values())
                    else 0,
                    2,
                ),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Provider status failed: {str(e)}")


@router.get("/performance/snapshot")
async def performance_snapshot() -> Dict[str, Any]:
    """Performance snapshot showing cache hit ratios, response times, and usage patterns"""
    try:
        # Get Redis info for cache metrics
        redis_info = {}
        try:
            if cache.redis:
                redis_info = await cache.redis.info()
        except Exception:
            pass

        # Calculate cache hit ratio
        cache_hits = int(redis_info.get("keyspace_hits", 0))
        cache_misses = int(redis_info.get("keyspace_misses", 0))
        total_requests = cache_hits + cache_misses
        cache_hit_ratio = round(
            (cache_hits / total_requests * 100) if total_requests > 0 else 0, 2
        )

        # Get overall performance metrics
        all_metrics = []
        for provider_name in performance_metrics.total_requests.keys():
            metrics = performance_metrics.get_metrics(provider_name)
            if metrics["total_requests"] > 0:
                all_metrics.append(metrics)

        avg_response_time = round(
            statistics.mean([m["avg_response_time"] for m in all_metrics])
            if all_metrics
            else 0,
            2,
        )
        avg_error_rate = round(
            statistics.mean([m["error_rate"] for m in all_metrics])
            if all_metrics
            else 0,
            2,
        )

        # Get task statistics
        all_tasks = await task_store.list_tasks()
        task_stats = {
            "total_tasks": len(all_tasks),
            "completed_tasks": len(
                [t for t in all_tasks if t.get("status") == "completed"]
            ),
            "failed_tasks": len([t for t in all_tasks if t.get("status") == "failed"]),
            "running_tasks": len(
                [t for t in all_tasks if t.get("status") == "running"]
            ),
            "queued_tasks": len([t for t in all_tasks if t.get("status") == "queued"]),
        }

        # Calculate streaming vs non-streaming usage
        streaming_tasks = len([t for t in all_tasks if t.get("streaming", False)])
        non_streaming_tasks = task_stats["total_tasks"] - streaming_tasks

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cache": {
                "hit_ratio": cache_hit_ratio,
                "hits": cache_hits,
                "misses": cache_misses,
                "total_requests": total_requests,
                "memory_usage": redis_info.get("used_memory_human", "unknown"),
                "connected_clients": redis_info.get("connected_clients", "unknown"),
            },
            "performance": {
                "avg_response_time": avg_response_time,
                "avg_error_rate": avg_error_rate,
                "total_requests": sum(m["total_requests"] for m in all_metrics),
                "total_errors": sum(m["error_count"] for m in all_metrics),
            },
            "tasks": task_stats,
            "usage": {
                "streaming_tasks": streaming_tasks,
                "non_streaming_tasks": non_streaming_tasks,
                "streaming_percentage": round(
                    (streaming_tasks / task_stats["total_tasks"] * 100)
                    if task_stats["total_tasks"] > 0
                    else 0,
                    2,
                ),
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Performance snapshot failed: {str(e)}"
        )


@router.get("/queues/snapshot")
async def queues_snapshot() -> Dict[str, Any]:
    """Task queue monitoring (read-only, no Flower dependency)"""
    try:
        # Get all tasks from task store
        all_tasks = await task_store.list_tasks()

        # Group tasks by status
        status_counts = defaultdict(int)
        for task in all_tasks:
            status = task.get("status", "unknown")
            status_counts[status] += 1

        # Get recent tasks (last 24 hours)
        recent_cutoff = time.time() - (24 * 3600)
        recent_tasks = [t for t in all_tasks if t.get("created_at", 0) > recent_cutoff]

        # Calculate task completion times
        completion_times = []
        for task in all_tasks:
            if (
                task.get("status") == "completed"
                and "created_at" in task
                and "updated_at" in task
            ):
                try:
                    created_str = task["created_at"]
                    updated_str = task["updated_at"]

                    # Handle different datetime formats
                    if created_str.endswith("Z"):
                        created_str = created_str.replace("Z", "+00:00")
                    if updated_str.endswith("Z"):
                        updated_str = updated_str.replace("Z", "+00:00")

                    created = datetime.fromisoformat(created_str)
                    updated = datetime.fromisoformat(updated_str)
                    duration = (updated - created).total_seconds()
                    if duration > 0:
                        completion_times.append(duration)
                except (ValueError, TypeError):
                    # Skip tasks with invalid datetime formats
                    continue

        avg_completion_time = (
            round(statistics.mean(completion_times), 2) if completion_times else 0
        )

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "queue_status": {
                "total_tasks": len(all_tasks),
                "recent_tasks_24h": len(recent_tasks),
                "active_tasks": status_counts.get("running", 0)
                + status_counts.get("queued", 0),
                "completed_tasks": status_counts.get("completed", 0),
                "failed_tasks": status_counts.get("failed", 0),
                "cancelled_tasks": status_counts.get("cancelled", 0),
            },
            "task_breakdown": dict(status_counts),
            "performance": {
                "avg_completion_time": avg_completion_time,
                "completion_rate": round(
                    (status_counts.get("completed", 0) / len(all_tasks) * 100)
                    if all_tasks
                    else 0,
                    2,
                ),
                "failure_rate": round(
                    (status_counts.get("failed", 0) / len(all_tasks) * 100)
                    if all_tasks
                    else 0,
                    2,
                ),
            },
            "queue_health": {
                "healthy": len(all_tasks) < 1000,  # Arbitrary threshold
                "backlog_size": status_counts.get("queued", 0),
                "stuck_tasks": len(
                    [
                        t
                        for t in all_tasks
                        if t.get("status") == "running"
                        and time.time() - t.get("created_at", 0) > 300
                    ]
                ),  # Tasks running > 5 minutes
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Queue snapshot failed: {str(e)}")


@router.get("/circuit-breakers")
async def circuit_breakers_status() -> Dict[str, Any]:
    """Circuit breaker states for all providers"""
    try:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "circuit_breakers": {
                name: cb.get_status() for name, cb in circuit_breakers.items()
            },
            "summary": {
                "total_breakers": len(circuit_breakers),
                "open_breakers": len(
                    [cb for cb in circuit_breakers.values() if cb.state == "OPEN"]
                ),
                "half_open_breakers": len(
                    [cb for cb in circuit_breakers.values() if cb.state == "HALF_OPEN"]
                ),
                "closed_breakers": len(
                    [cb for cb in circuit_breakers.values() if cb.state == "CLOSED"]
                ),
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Circuit breaker status failed: {str(e)}"
        )


@router.post("/circuit-breakers/{provider_name}/reset")
async def reset_circuit_breaker(provider_name: str) -> Dict[str, Any]:
    """Reset circuit breaker for a specific provider"""
    try:
        if provider_name not in circuit_breakers:
            circuit_breakers[provider_name] = CircuitBreaker()

        cb = circuit_breakers[provider_name]
        cb.failure_count = 0
        cb.state = "CLOSED"
        cb.last_failure_time = 0

        return {
            "provider": provider_name,
            "status": "reset",
            "circuit_breaker": cb.get_status(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to reset circuit breaker: {str(e)}"
        )


@router.get("/metrics/history")
async def metrics_history(
    provider: str = Query(None, description="Provider name to get history for"),
    metric: str = Query("response_time", description="Metric to get history for"),
    hours: int = Query(1, description="Number of hours to look back"),
) -> Dict[str, Any]:
    """Get historical metrics for a provider"""
    try:
        if provider:
            # Get specific provider history
            times = performance_metrics.response_times.get(provider, [])
            if not times:
                return {"provider": provider, "metric": metric, "history": []}

            # Return last N measurements (configurable)
            return {
                "provider": provider,
                "metric": metric,
                "history": times[-100:],  # Last 100 measurements
                "avg": round(statistics.mean(times), 2) if times else 0,
                "min": round(min(times), 2) if times else 0,
                "max": round(max(times), 2) if times else 0,
            }
        else:
            # Get system-wide history
            all_history = {}
            for prov_name in performance_metrics.total_requests.keys():
                times = performance_metrics.response_times.get(prov_name, [])
                if times:
                    all_history[prov_name] = {
                        "history": times[-50:],  # Last 50 measurements per provider
                        "avg": round(statistics.mean(times), 2),
                        "min": round(min(times), 2),
                        "max": round(max(times), 2),
                    }

            return {
                "metric": metric,
                "history": all_history,
                "timestamp": datetime.utcnow().isoformat(),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metrics history failed: {str(e)}")


# Enhanced endpoints using the new aggregation system
@router.get("/aggregated")
@require_ops_access("read")
async def get_aggregated_metrics(request: Request) -> Dict[str, Any]:
    """Get fully aggregated and normalized system metrics"""
    try:
        # Initialize aggregator if not already done
        await aggregator.initialize()

        # Get aggregated metrics
        aggregated = await aggregator.aggregate_system_metrics()

        return {
            "success": True,
            "data": aggregated,
            "message": "Aggregated metrics retrieved successfully",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get aggregated metrics: {str(e)}"
        )


@router.get("/health/trends")
@require_ops_access("read")
async def get_health_trends(request: Request) -> Dict[str, Any]:
    """Get health score trends and predictions"""
    try:
        # Get current aggregated metrics
        aggregated = await aggregator.aggregate_system_metrics()

        # Calculate trend analysis
        trends = {
            "system_health_trend": aggregated.get("health", {}).get("trend", "unknown"),
            "provider_health_trend": "stable",  # Would need historical data
            "performance_trend": "stable",  # Would need historical data
            "predictions": {
                "next_hour": "stable",  # Placeholder for ML predictions
                "next_day": "stable",
            },
        }

        return {
            "success": True,
            "data": trends,
            "message": "Health trends calculated successfully",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get health trends: {str(e)}"
        )


@router.get("/streaming/analysis")
@require_ops_access("read")
async def get_streaming_analysis(request: Request) -> Dict[str, Any]:
    """Get detailed streaming vs non-streaming performance analysis"""
    try:
        # Get current aggregated metrics
        aggregated = await aggregator.aggregate_system_metrics()

        streaming_data = aggregated.get("streaming", {})

        # Add cost analysis
        analysis = {
            "efficiency_comparison": streaming_data.get("comparison", {}),
            "cost_analysis": {
                "streaming_cost_estimate": "N/A",  # Would need actual cost data
                "batch_cost_estimate": "N/A",
                "cost_difference": "N/A",
            },
            "recommendations": [
                "Monitor streaming completion rates vs batch processing",
                "Consider circuit breaker thresholds for streaming operations",
                "Evaluate memory usage patterns for long-running streams",
            ],
        }

        return {
            "success": True,
            "data": analysis,
            "message": "Streaming analysis completed successfully",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get streaming analysis: {str(e)}"
        )


@router.get("/security/status")
@require_ops_access("read")
async def get_security_status(request: Request) -> Dict[str, Any]:
    """Get operational security status and configuration"""
    try:
        security_summary = get_security_summary()

        return {
            "success": True,
            "data": security_summary,
            "message": "Security status retrieved successfully",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get security status: {str(e)}"
        )


@router.get("/audit/log")
@require_ops_access("read")
async def get_audit_log(
    request: Request,
    limit: int = Query(100, description="Number of log entries to return"),
    offset: int = Query(0, description="Offset for pagination"),
) -> Dict[str, Any]:
    """Get audit log for operational activities"""
    try:
        audit_log = await get_ops_audit_log(limit=limit, offset=offset)

        return {
            "success": True,
            "data": {
                "audit_log": audit_log,
                "total_entries": len(audit_log),
                "limit": limit,
                "offset": offset,
            },
            "message": "Audit log retrieved successfully",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get audit log: {str(e)}"
        )


@router.post("/circuit-breakers/{provider_name}/reset")
@require_ops_reset_access()
async def reset_circuit_breaker_enhanced(
    request: Request, provider_name: str
) -> Dict[str, Any]:
    """Enhanced circuit breaker reset with audit logging"""
    try:
        if provider_name not in circuit_breakers:
            circuit_breakers[provider_name] = CircuitBreaker()

        cb = circuit_breakers[provider_name]
        old_state = cb.state

        cb.failure_count = 0
        cb.state = "CLOSED"
        cb.last_failure_time = 0

        return {
            "success": True,
            "data": {
                "provider": provider_name,
                "status": "reset",
                "previous_state": old_state,
                "new_state": cb.state,
                "circuit_breaker": cb.get_status(),
            },
            "message": f"Circuit breaker for {provider_name} reset successfully",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to reset circuit breaker: {str(e)}"
        )


@router.get("/recommendations")
@require_ops_access("read")
async def get_system_recommendations(request: Request) -> Dict[str, Any]:
    """Get AI-driven system recommendations based on aggregated metrics"""
    try:
        # Get current aggregated metrics
        aggregated = await aggregator.aggregate_system_metrics()

        # Get recommendations from the aggregator
        recommendations = aggregated.get("summary", {}).get("recommendations", [])

        # Add environment-specific recommendations
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env == "production":
            recommendations.extend(
                [
                    "Enable production-specific monitoring alerts",
                    "Review circuit breaker thresholds for production load",
                    "Consider implementing predictive failure detection",
                ]
            )
        elif env == "development":
            recommendations.extend(
                [
                    "Enable debug logging for development troubleshooting",
                    "Test circuit breaker behavior with simulated failures",
                    "Monitor resource usage during development testing",
                ]
            )

        return {
            "success": True,
            "data": {
                "recommendations": recommendations,
                "priority": "medium",  # Would be calculated based on health scores
                "last_updated": datetime.utcnow().isoformat(),
            },
            "message": "System recommendations generated successfully",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get recommendations: {str(e)}"
        )


def _calculate_health_score(
    status: Dict[str, Any], metrics: Dict[str, Any], cb: CircuitBreaker
) -> float:
    """Calculate health score for a provider (0-100)"""
    score = 100.0

    # Status penalty
    if status.get("status") != "healthy":
        score -= 30

    # Circuit breaker penalty
    if cb.state == "OPEN":
        score -= 40
    elif cb.state == "HALF_OPEN":
        score -= 20

    # Error rate penalty
    error_rate = metrics.get("error_rate", 0)
    if error_rate > 10:
        score -= 20
    elif error_rate > 5:
        score -= 10
    elif error_rate > 1:
        score -= 5

    # Response time penalty (if > 5 seconds average)
    avg_time = metrics.get("avg_response_time", 0)
    if avg_time > 5000:
        score -= 10
    elif avg_time > 2000:
        score -= 5

    return max(0, round(score, 1))
