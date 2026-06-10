"""Backward-compatible re-exports for ops_routes.

Previously contained CircuitBreaker, PerformanceMetrics, and calculate_health_score.
These have been moved to the ops/ domain layer for better separation of concerns.
"""

from ..ops.circuit_breaker import CircuitBreaker, calculate_health_score
from ..ops.performance_metrics import PerformanceMetrics, performance_metrics

circuit_breakers: dict = {}

__all__ = [
    "CircuitBreaker",
    "PerformanceMetrics",
    "calculate_health_score",
    "circuit_breakers",
    "performance_metrics",
]
