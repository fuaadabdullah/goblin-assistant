"""
Observability Package
Provides comprehensive observability and debugging capabilities for the goblin-assistant

This package implements the "Prime Directive": If a decision affects memory, retrieval,
routing, or context, it must be inspectable. No black boxes. No "the model decided."

Components:
- Decision Logger: Tracks write-time decisions with full context
- Memory Logger: Logs memory promotion events with audit trail
- Retrieval Tracer: The crown jewel - traces every LLM call with full retrieval details
- Context Snapshotter: Captures redacted context snapshots for debugging
- Metrics Collector: Aggregates observability metrics for health monitoring
- Alerting System: Monitors system health and alerts on issues
- Debug Router: Provides debug surfaces for inspection
"""

from .alerting_system import Alert, AlertSeverity, AlertStatus, alerting_system
from .context_snapshotter import capture_context_snapshot, context_snapshotter
from .debug_router import router as debug_router
from .decision_logger import DecisionReason, decision_logger, log_write_time_decision
from .memory_logger import PromotionGate, log_memory_promotion, memory_promotion_logger
from .metrics_collector import SystemMetrics, metrics_collector
from .retrieval_tracer import (
    RetrievalTier,
    RetrievedItem,
    retrieval_tracer,
    trace_retrieval,
)


# Initialize observability systems
async def initialize_observability():
    """Initialize all observability systems"""
    try:
        # Start alerting system monitoring
        await alerting_system.start_monitoring()

        return {
            "success": True,
            "message": "Observability systems initialized successfully",
            "components": [
                "decision_logger",
                "memory_logger",
                "retrieval_tracer",
                "context_snapshotter",
                "metrics_collector",
                "alerting_system",
                "debug_router",
            ],
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to initialize observability systems: {str(e)}",
            "error": str(e),
        }


# Export all components
__all__ = [
    # Core components
    "decision_logger",
    "memory_promotion_logger",
    "retrieval_tracer",
    "context_snapshotter",
    "metrics_collector",
    "alerting_system",
    "debug_router",
    # Enums
    "DecisionReason",
    "PromotionGate",
    "RetrievalTier",
    "AlertSeverity",
    "AlertStatus",
    # Data classes
    "RetrievedItem",
    "SystemMetrics",
    "Alert",
    # Functions
    "log_write_time_decision",
    "log_memory_promotion",
    "trace_retrieval",
    "capture_context_snapshot",
    "initialize_observability",
]

# Version information
__version__ = "1.0.0"
__description__ = "Comprehensive observability and debugging system for goblin-assistant"
