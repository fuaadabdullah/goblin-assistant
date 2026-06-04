import os
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from ..ops.aggregator import aggregator
from ..ops.security import require_ops_access

router = APIRouter()


@router.get("/aggregated")
@require_ops_access("read")
async def get_aggregated_metrics(request: Request) -> Dict[str, Any]:
    try:
        await aggregator.initialize()
        aggregated = await aggregator.aggregate_system_metrics()
        return {
            "success": True,
            "data": aggregated,
            "message": "Aggregated metrics retrieved successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get aggregated metrics: {str(e)}")


@router.get("/health/trends")
@require_ops_access("read")
async def get_health_trends(request: Request) -> Dict[str, Any]:
    try:
        aggregated = await aggregator.aggregate_system_metrics()
        trends = {
            "system_health_trend": aggregated.get("health", {}).get("trend", "unknown"),
            "provider_health_trend": "stable",
            "performance_trend": "stable",
            "predictions": {
                "next_hour": "stable",
                "next_day": "stable",
            },
        }

        return {
            "success": True,
            "data": trends,
            "message": "Health trends calculated successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get health trends: {str(e)}")


@router.get("/streaming/analysis")
@require_ops_access("read")
async def get_streaming_analysis(request: Request) -> Dict[str, Any]:
    try:
        aggregated = await aggregator.aggregate_system_metrics()
        streaming_data = aggregated.get("streaming", {})

        analysis = {
            "efficiency_comparison": streaming_data.get("comparison", {}),
            "cost_analysis": {
                "streaming_cost_estimate": "N/A",
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
        raise HTTPException(status_code=500, detail=f"Failed to get streaming analysis: {str(e)}")


@router.get("/recommendations")
@require_ops_access("read")
async def get_system_recommendations(request: Request) -> Dict[str, Any]:
    try:
        aggregated = await aggregator.aggregate_system_metrics()
        recommendations = aggregated.get("summary", {}).get("recommendations", [])

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
                "priority": "medium",
                "last_updated": datetime.utcnow().isoformat(),
            },
            "message": "System recommendations generated successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")
