"""
Context Assembly Monitoring and Observability Service

Provides comprehensive monitoring, logging, and debugging capabilities for the
Retrieval Ordering + Token Budgeting system. This service tracks:
- Context assembly performance metrics
- Token usage patterns
- Layer effectiveness analysis
- Debug information for troubleshooting
"""

import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import structlog
import asyncio

from .context_assembly_service import ContextAssemblyService, ContextLayer, ContextBudget
from ..config.system_prompt import SystemPromptManager

logger = structlog.get_logger()


@dataclass
class AssemblyMetrics:
    """Metrics for a single context assembly operation"""
    assembly_id: str
    user_id: Optional[str]
    conversation_id: Optional[str]
    query: str
    layers_assembled: int
    total_tokens_used: int
    remaining_tokens: int
    assembly_duration_ms: float
    layers: List[Dict[str, Any]]
    success: bool
    error: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class BudgetMetrics:
    """Token budget utilization metrics"""
    budget_config: Dict[str, int]
    average_tokens_used: float
    average_remaining_tokens: float
    budget_exceeded_count: int
    hard_stop_triggered_count: int
    last_reset_time: str


class ContextMonitoringService:
    """
    Service for monitoring and debugging context assembly operations.
    
    Features:
    - Real-time assembly metrics tracking
    - Token budget utilization analysis
    - Performance monitoring
    - Debug information collection
    - Historical metrics storage
    """
    
    def __init__(self):
        self.assembly_service: Optional[ContextAssemblyService] = None
        self.system_prompt_manager: Optional[SystemPromptManager] = None
        
        # In-memory metrics storage (could be persisted to database)
        self.assembly_metrics: List[AssemblyMetrics] = []
        self.budget_metrics: BudgetMetrics = self._init_budget_metrics()
        
        # Performance tracking
        self.assembly_times: List[float] = []
        self.error_count = 0
        self.success_count = 0
        
        # Layer effectiveness tracking
        self.layer_effectiveness: Dict[str, Dict[str, int]] = {
            "system": {"success": 0, "skipped": 0, "failed": 0},
            "long_term_memory": {"success": 0, "skipped": 0, "failed": 0},
            "working_memory": {"success": 0, "skipped": 0, "failed": 0},
            "semantic_retrieval": {"success": 0, "skipped": 0, "failed": 0},
            "ephemeral_memory": {"success": 0, "skipped": 0, "failed": 0}
        }
    
    def initialize(self, assembly_service: ContextAssemblyService, system_prompt_manager: SystemPromptManager):
        """Initialize with required services"""
        self.assembly_service = assembly_service
        self.system_prompt_manager = system_prompt_manager
    
    def _init_budget_metrics(self) -> BudgetMetrics:
        """Initialize budget metrics with default configuration"""
        return BudgetMetrics(
            budget_config={
                "total_tokens": 8000,
                "system_tokens": 300,
                "long_term_tokens": 300,
                "working_memory_tokens": 700,
                "semantic_retrieval_tokens": 1200,
                "ephemeral_tokens": 5500
            },
            average_tokens_used=0.0,
            average_remaining_tokens=0.0,
            budget_exceeded_count=0,
            hard_stop_triggered_count=0,
            last_reset_time=datetime.utcnow().isoformat()
        )
    
    async def track_assembly(
        self,
        assembly_result: Dict[str, Any],
        user_id: Optional[str],
        conversation_id: Optional[str],
        query: str,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """
        Track a context assembly operation
        
        Args:
            assembly_result: Result from context assembly service
            user_id: User identifier
            conversation_id: Conversation identifier
            query: User query
            success: Whether assembly succeeded
            error: Error message if failed
        """
        try:
            # Calculate assembly duration from assembly log if available
            assembly_time = 0.0
            layers = []
            
            if "assembly_log" in assembly_result:
                assembly_log = assembly_result["assembly_log"]
                start_time = datetime.fromisoformat(assembly_log.get("assembly_time", datetime.utcnow().isoformat()))
                end_time = datetime.utcnow()
                assembly_time = (end_time - start_time).total_seconds() * 1000
                
                # Extract layer information
                for layer_name in assembly_log.get("layers", []):
                    layer_tokens = assembly_log.get("token_usage", {}).get(layer_name, 0)
                    layers.append({
                        "name": layer_name,
                        "tokens": layer_tokens,
                        "success": True
                    })
            
            # Create metrics record
            metrics = AssemblyMetrics(
                assembly_id=f"assembly_{int(time.time() * 1000)}",
                user_id=user_id,
                conversation_id=conversation_id,
                query=query,
                layers_assembled=len(layers),
                total_tokens_used=assembly_result.get("total_tokens_used", 0),
                remaining_tokens=assembly_result.get("remaining_tokens", 0),
                assembly_duration_ms=assembly_time,
                layers=layers,
                success=success,
                error=error
            )
            
            # Store metrics
            self.assembly_metrics.append(metrics)
            
            # Update counters
            if success:
                self.success_count += 1
            else:
                self.error_count += 1
            
            # Update assembly times
            if assembly_time > 0:
                self.assembly_times.append(assembly_time)
                if len(self.assembly_times) > 100:  # Keep last 100 measurements
                    self.assembly_times.pop(0)
            
            # Update layer effectiveness
            for layer in layers:
                layer_name = layer["name"]
                if layer_name in self.layer_effectiveness:
                    self.layer_effectiveness[layer_name]["success"] += 1
            
            # Update budget metrics
            self._update_budget_metrics(metrics)
            
            # Log assembly completion
            logger.info(
                "Context assembly tracked",
                assembly_id=metrics.assembly_id,
                user_id=user_id,
                conversation_id=conversation_id,
                layers=len(layers),
                tokens_used=metrics.total_tokens_used,
                remaining_tokens=metrics.remaining_tokens,
                duration_ms=assembly_time,
                success=success
            )
            
        except Exception as e:
            logger.error("Failed to track assembly metrics", error=str(e))
    
    def _update_budget_metrics(self, metrics: AssemblyMetrics):
        """Update budget utilization metrics"""
        # Update averages
        total_assemblies = self.success_count + self.error_count
        if total_assemblies > 0:
            self.budget_metrics.average_tokens_used = (
                sum(m.total_tokens_used for m in self.assembly_metrics) / total_assemblies
            )
            self.budget_metrics.average_remaining_tokens = (
                sum(m.remaining_tokens for m in self.assembly_metrics) / total_assemblies
            )
        
        # Check for budget exceeded
        if metrics.total_tokens_used > self.budget_metrics.budget_config["total_tokens"]:
            self.budget_metrics.budget_exceeded_count += 1
        
        # Check for hard stops (when layers were skipped due to budget)
        if metrics.remaining_tokens == 0 and metrics.layers_assembled < 5:
            self.budget_metrics.hard_stop_triggered_count += 1
    
    def get_assembly_performance(self) -> Dict[str, Any]:
        """Get assembly performance metrics"""
        total_assemblies = self.success_count + self.error_count
        
        if total_assemblies == 0:
            return {
                "total_assemblies": 0,
                "success_rate": 0.0,
                "error_rate": 0.0,
                "average_assembly_time_ms": 0.0,
                "layer_effectiveness": self.layer_effectiveness
            }
        
        success_rate = (self.success_count / total_assemblies) * 100
        error_rate = (self.error_count / total_assemblies) * 100
        avg_assembly_time = sum(self.assembly_times) / len(self.assembly_times) if self.assembly_times else 0.0
        
        return {
            "total_assemblies": total_assemblies,
            "success_rate": round(success_rate, 2),
            "error_rate": round(error_rate, 2),
            "average_assembly_time_ms": round(avg_assembly_time, 2),
            "layer_effectiveness": self.layer_effectiveness,
            "recent_assemblies": [
                {
                    "assembly_id": m.assembly_id,
                    "success": m.success,
                    "layers": m.layers_assembled,
                    "tokens_used": m.total_tokens_used,
                    "duration_ms": m.assembly_duration_ms
                }
                for m in self.assembly_metrics[-10:]  # Last 10 assemblies
            ]
        }
    
    def get_budget_utilization(self) -> Dict[str, Any]:
        """Get token budget utilization metrics"""
        return {
            "budget_config": self.budget_metrics.budget_config,
            "average_tokens_used": round(self.budget_metrics.average_tokens_used, 2),
            "average_remaining_tokens": round(self.budget_metrics.average_remaining_tokens, 2),
            "budget_exceeded_count": self.budget_metrics.budget_exceeded_count,
            "hard_stop_triggered_count": self.budget_metrics.hard_stop_triggered_count,
            "budget_efficiency": self._calculate_budget_efficiency(),
            "last_reset_time": self.budget_metrics.last_reset_time
        }
    
    def _calculate_budget_efficiency(self) -> float:
        """Calculate budget utilization efficiency"""
        if not self.assembly_metrics:
            return 0.0
        
        total_budget = self.budget_metrics.budget_config["total_tokens"]
        total_used = sum(m.total_tokens_used for m in self.assembly_metrics)
        total_possible = len(self.assembly_metrics) * total_budget
        
        if total_possible == 0:
            return 0.0
        
        return round((total_used / total_possible) * 100, 2)
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get comprehensive debug information"""
        return {
            "assembly_service": self.assembly_service.get_debug_info() if self.assembly_service else {},
            "system_prompt": self.system_prompt_manager.get_debug_info() if self.system_prompt_manager else {},
            "performance": self.get_assembly_performance(),
            "budget_utilization": self.get_budget_utilization(),
            "layer_effectiveness": self.layer_effectiveness,
            "monitoring_stats": {
                "total_metrics_stored": len(self.assembly_metrics),
                "success_count": self.success_count,
                "error_count": self.error_count,
                "assembly_times_count": len(self.assembly_times)
            }
        }
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get optimization recommendations based on metrics"""
        recommendations = []
        
        # Check assembly performance
        performance = self.get_assembly_performance()
        if performance["average_assembly_time_ms"] > 1000:  # > 1 second
            recommendations.append({
                "type": "performance",
                "priority": "high",
                "issue": "Slow context assembly",
                "recommendation": "Consider caching frequently accessed memory facts or optimizing retrieval queries",
                "current_value": f"{performance['average_assembly_time_ms']}ms",
                "target_value": "< 500ms"
            })
        
        # Check success rate
        if performance["success_rate"] < 95:
            recommendations.append({
                "type": "reliability",
                "priority": "high",
                "issue": "Low assembly success rate",
                "recommendation": "Investigate common failure patterns and add error handling",
                "current_value": f"{performance['success_rate']}%",
                "target_value": "> 95%"
            })
        
        # Check budget utilization
        budget_util = self.get_budget_utilization()
        if budget_util["budget_efficiency"] < 50:
            recommendations.append({
                "type": "efficiency",
                "priority": "medium",
                "issue": "Low budget utilization",
                "recommendation": "Consider reducing context window size or increasing content density",
                "current_value": f"{budget_util['budget_efficiency']}%",
                "target_value": "> 70%"
            })
        
        # Check hard stop frequency
        if budget_util["hard_stop_triggered_count"] > 10:
            recommendations.append({
                "type": "capacity",
                "priority": "medium",
                "issue": "Frequent hard stops",
                "recommendation": "Consider increasing context window size or optimizing content trimming",
                "current_value": f"{budget_util['hard_stop_triggered_count']} triggers",
                "target_value": "< 5 triggers"
            })
        
        # Check layer effectiveness
        for layer_name, stats in self.layer_effectiveness.items():
            total_attempts = stats["success"] + stats["skipped"] + stats["failed"]
            if total_attempts > 0:
                success_rate = (stats["success"] / total_attempts) * 100
                if success_rate < 80:
                    recommendations.append({
                        "type": "layer_optimization",
                        "priority": "low",
                        "issue": f"Low {layer_name} layer success rate",
                        "recommendation": f"Investigate why {layer_name} layer frequently fails or gets skipped",
                        "current_value": f"{success_rate}%",
                        "target_value": "> 80%"
                    })
        
        return recommendations
    
    def reset_metrics(self) -> None:
        """Reset all metrics and start fresh"""
        self.assembly_metrics.clear()
        self.assembly_times.clear()
        self.error_count = 0
        self.success_count = 0
        self.layer_effectiveness = {
            "system": {"success": 0, "skipped": 0, "failed": 0},
            "long_term_memory": {"success": 0, "skipped": 0, "failed": 0},
            "working_memory": {"success": 0, "skipped": 0, "failed": 0},
            "semantic_retrieval": {"success": 0, "skipped": 0, "failed": 0},
            "ephemeral_memory": {"success": 0, "skipped": 0, "failed": 0}
        }
        self.budget_metrics = self._init_budget_metrics()
        
        logger.info("Context monitoring metrics reset")
    
    async def run_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check"""
        try:
            health_status = {
                "status": "healthy",
                "checks": [],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Check assembly service
            if self.assembly_service:
                try:
                    debug_info = self.assembly_service.get_debug_info()
                    health_status["checks"].append({
                        "name": "assembly_service",
                        "status": "healthy",
                        "details": f"Budget: {debug_info['budget']['total_tokens']} tokens"
                    })
                except Exception as e:
                    health_status["checks"].append({
                        "name": "assembly_service",
                        "status": "unhealthy",
                        "error": str(e)
                    })
                    health_status["status"] = "degraded"
            else:
                health_status["checks"].append({
                    "name": "assembly_service",
                    "status": "unhealthy",
                    "error": "Not initialized"
                })
                health_status["status"] = "unhealthy"
            
            # Check system prompt manager
            if self.system_prompt_manager:
                try:
                    debug_info = self.system_prompt_manager.get_debug_info()
                    health_status["checks"].append({
                        "name": "system_prompt_manager",
                        "status": "healthy",
                        "details": f"Prompt length: {debug_info['prompt_length']} chars"
                    })
                except Exception as e:
                    health_status["checks"].append({
                        "name": "system_prompt_manager",
                        "status": "unhealthy",
                        "error": str(e)
                    })
                    health_status["status"] = "degraded"
            else:
                health_status["checks"].append({
                    "name": "system_prompt_manager",
                    "status": "unhealthy",
                    "error": "Not initialized"
                })
                health_status["status"] = "unhealthy"
            
            # Check performance metrics
            performance = self.get_assembly_performance()
            if performance["success_rate"] < 80:
                health_status["checks"].append({
                    "name": "performance",
                    "status": "unhealthy",
                    "error": f"Success rate too low: {performance['success_rate']}%"
                })
                health_status["status"] = "unhealthy"
            else:
                health_status["checks"].append({
                    "name": "performance",
                    "status": "healthy",
                    "details": f"Success rate: {performance['success_rate']}%"
                })
            
            # Check budget utilization
            budget_util = self.get_budget_utilization()
            if budget_util["hard_stop_triggered_count"] > 20:
                health_status["checks"].append({
                    "name": "budget_utilization",
                    "status": "degraded",
                    "error": f"Too many hard stops: {budget_util['hard_stop_triggered_count']}"
                })
                if health_status["status"] == "healthy":
                    health_status["status"] = "degraded"
            
            return health_status
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Global instance
context_monitoring_service = ContextMonitoringService()