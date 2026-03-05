"""
Metrics Collector
Aggregates observability metrics and provides health monitoring
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import statistics
import structlog

from .decision_logger import decision_logger
from .memory_logger import memory_promotion_logger
from .retrieval_tracer import retrieval_tracer
from .context_snapshotter import context_snapshotter
from ..config.system_config import get_system_config

logger = structlog.get_logger()


@dataclass
class SystemMetrics:
    """Aggregated system metrics"""
    timestamp: datetime
    memory_health: Dict[str, Any]
    retrieval_quality: Dict[str, Any]
    context_assembly: Dict[str, Any]
    write_time_decisions: Dict[str, Any]
    overall_health_score: float
    recommendations: List[str]


class MetricsCollector:
    """Centralized metrics collection and health monitoring"""
    
    def __init__(self):
        self.config = get_system_config()
        self._metrics_cache = {}
        self._cache_ttl = 30  # 30 seconds cache
    
    async def collect_system_metrics(
        self, 
        user_id: Optional[str] = None,
        time_window_hours: int = 24
    ) -> SystemMetrics:
        """Collect comprehensive system metrics"""
        
        try:
            # Collect metrics from all observability systems
            decision_stats = await decision_logger.get_decision_stats(
                user_id=user_id,
                time_window_hours=time_window_hours
            )
            
            memory_stats = await memory_promotion_logger.get_promotion_stats(
                user_id=user_id,
                time_window_hours=time_window_hours
            )
            
            retrieval_stats = await retrieval_tracer.get_retrieval_stats(
                user_id=user_id,
                time_window_hours=time_window_hours
            )
            
            context_stats = await context_snapshotter.get_context_assembly_stats(
                user_id=user_id,
                time_window_hours=time_window_hours
            )
            
            # Calculate health scores
            memory_health = await self._calculate_memory_health(memory_stats)
            retrieval_quality = await self._calculate_retrieval_quality(retrieval_stats)
            context_assembly = await self._calculate_context_health(context_stats)
            write_time_decisions = await self._calculate_decision_health(decision_stats)
            
            # Calculate overall health score
            overall_health_score = self._calculate_overall_health(
                memory_health, retrieval_quality, context_assembly, write_time_decisions
            )
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(
                memory_health, retrieval_quality, context_assembly, write_time_decisions
            )
            
            metrics = SystemMetrics(
                timestamp=datetime.utcnow(),
                memory_health=memory_health,
                retrieval_quality=retrieval_quality,
                context_assembly=context_assembly,
                write_time_decisions=write_time_decisions,
                overall_health_score=overall_health_score,
                recommendations=recommendations
            )
            
            # Cache the metrics
            self._metrics_cache[f"{user_id}:{time_window_hours}"] = {
                "metrics": metrics,
                "expires_at": datetime.utcnow().timestamp() + self._cache_ttl
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return SystemMetrics(
                timestamp=datetime.utcnow(),
                memory_health={"error": str(e)},
                retrieval_quality={"error": str(e)},
                context_assembly={"error": str(e)},
                write_time_decisions={"error": str(e)},
                overall_health_score=0.0,
                recommendations=["System metrics collection failed"]
            )
    
    async def _calculate_memory_health(self, memory_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate memory system health metrics"""
        if not memory_stats or memory_stats.get("total_attempts", 0) == 0:
            return {"status": "no_data", "score": 0}
        
        # Key metrics
        total_attempts = memory_stats.get("total_attempts", 0)
        promotion_rate = memory_stats.get("promotion_rate", 0)
        avg_confidence = memory_stats.get("avg_confidence", {}).get("promoted", 0)
        
        # Calculate health score (0-100)
        score = 50  # Base score
        
        # Promotion rate health
        if 10 <= promotion_rate <= 30:  # Good promotion rate range
            score += 25
        elif 5 <= promotion_rate < 10 or 30 < promotion_rate <= 50:
            score += 10
        # Below 5% or above 50% is concerning
        
        # Confidence health
        if avg_confidence >= 0.8:
            score += 25
        elif avg_confidence >= 0.6:
            score += 15
        elif avg_confidence >= 0.4:
            score += 5
        
        # Gate failure analysis
        gates_failed = memory_stats.get("gate_analysis", {}).get("gates_failed", {})
        total_failures = sum(gates_failed.values())
        if total_failures == 0:
            score += 10
        elif total_failures < total_attempts * 0.2:  # Less than 20% failure rate
            score += 5
        
        return {
            "status": "healthy" if score >= 70 else "warning" if score >= 40 else "critical",
            "score": min(100, score),
            "total_attempts": total_attempts,
            "promotion_rate": promotion_rate,
            "avg_confidence": avg_confidence,
            "gate_failures": total_failures
        }
    
    async def _calculate_retrieval_quality(self, retrieval_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate retrieval system quality metrics"""
        if not retrieval_stats or retrieval_stats.get("total_retrievals", 0) == 0:
            return {"status": "no_data", "score": 0}
        
        # Key metrics
        total_retrievals = retrieval_stats.get("total_retrievals", 0)
        avg_relevance = retrieval_stats.get("retrieval_quality", {}).get("avg_relevance", 0)
        token_utilization = retrieval_stats.get("token_usage", {}).get("avg_token_utilization", 0)
        error_rate = retrieval_stats.get("error_rate", 0)
        
        # Calculate health score (0-100)
        score = 50  # Base score
        
        # Relevance health
        if avg_relevance >= 0.8:
            score += 25
        elif avg_relevance >= 0.6:
            score += 15
        elif avg_relevance >= 0.4:
            score += 5
        
        # Token utilization health
        if 50 <= token_utilization <= 90:  # Good utilization range
            score += 20
        elif 30 <= token_utilization < 50 or 90 < token_utilization <= 95:
            score += 10
        
        # Error rate health
        if error_rate <= 5:
            score += 15
        elif error_rate <= 10:
            score += 5
        
        return {
            "status": "healthy" if score >= 70 else "warning" if score >= 40 else "critical",
            "score": min(100, score),
            "total_retrievals": total_retrievals,
            "avg_relevance": avg_relevance,
            "token_utilization": token_utilization,
            "error_rate": error_rate
        }
    
    async def _calculate_context_health(self, context_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate context assembly health metrics"""
        if not context_stats or context_stats.get("total_assemblies", 0) == 0:
            return {"status": "no_data", "score": 0}
        
        # Key metrics
        total_assemblies = context_stats.get("total_assemblies", 0)
        avg_assembly_time = context_stats.get("assembly_stats", {}).get("avg_assembly_time", 0)
        token_utilization = context_stats.get("token_stats", {}).get("avg_token_utilization", 0)
        error_rate = context_stats.get("error_rate", 0)
        redaction_rate = context_stats.get("redaction_stats", {}).get("redaction_rate", 0)
        
        # Calculate health score (0-100)
        score = 50  # Base score
        
        # Assembly time health
        if avg_assembly_time <= 100:  # Less than 100ms is good
            score += 20
        elif avg_assembly_time <= 500:
            score += 10
        elif avg_assembly_time <= 1000:
            score += 5
        
        # Token utilization health
        if 60 <= token_utilization <= 90:
            score += 15
        elif 40 <= token_utilization < 60 or 90 < token_utilization <= 95:
            score += 8
        
        # Error rate health
        if error_rate <= 5:
            score += 10
        elif error_rate <= 10:
            score += 5
        
        # Redaction rate health
        if redaction_rate <= 15:  # Normal amount of redaction
            score += 5
        elif redaction_rate <= 25:
            score += 2
        
        return {
            "status": "healthy" if score >= 70 else "warning" if score >= 40 else "critical",
            "score": min(100, score),
            "total_assemblies": total_assemblies,
            "avg_assembly_time": avg_assembly_time,
            "token_utilization": token_utilization,
            "error_rate": error_rate,
            "redaction_rate": redaction_rate
        }
    
    async def _calculate_decision_health(self, decision_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate write-time decision health metrics"""
        if not decision_stats or decision_stats.get("total_decisions", 0) == 0:
            return {"status": "no_data", "score": 0}
        
        # Key metrics
        total_decisions = decision_stats.get("total_decisions", 0)
        avg_confidence = decision_stats.get("avg_confidence", 0)
        outcome_stats = decision_stats.get("outcome_stats", {})
        
        # Calculate health score (0-100)
        score = 50  # Base score
        
        # Confidence health
        if avg_confidence >= 0.8:
            score += 25
        elif avg_confidence >= 0.6:
            score += 15
        elif avg_confidence >= 0.4:
            score += 5
        
        # Outcome distribution health
        total_processed = outcome_stats.get("embedded", 0) + outcome_stats.get("summarized", 0)
        if total_processed > 0:
            # Good balance between processed and stored messages
            processed_ratio = total_processed / total_decisions
            if 0.1 <= processed_ratio <= 0.5:  # Reasonable processing rate
                score += 25
            elif 0.05 <= processed_ratio < 0.1 or 0.5 < processed_ratio <= 0.7:
                score += 15
        
        return {
            "status": "healthy" if score >= 70 else "warning" if score >= 40 else "critical",
            "score": min(100, score),
            "total_decisions": total_decisions,
            "avg_confidence": avg_confidence,
            "outcome_distribution": outcome_stats
        }
    
    def _calculate_overall_health(
        self, 
        memory_health: Dict[str, Any], 
        retrieval_quality: Dict[str, Any],
        context_assembly: Dict[str, Any], 
        write_time_decisions: Dict[str, Any]
    ) -> float:
        """Calculate overall system health score"""
        
        scores = []
        
        if memory_health.get("score", 0) > 0:
            scores.append(memory_health["score"])
        
        if retrieval_quality.get("score", 0) > 0:
            scores.append(retrieval_quality["score"])
        
        if context_assembly.get("score", 0) > 0:
            scores.append(context_assembly["score"])
        
        if write_time_decisions.get("score", 0) > 0:
            scores.append(write_time_decisions["score"])
        
        if not scores:
            return 0.0
        
        # Weighted average (memory and retrieval are most important)
        weights = [0.3, 0.3, 0.2, 0.2]  # memory, retrieval, context, decisions
        weighted_score = sum(score * weight for score, weight in zip(scores, weights))
        
        return round(weighted_score, 1)
    
    async def _generate_recommendations(
        self,
        memory_health: Dict[str, Any],
        retrieval_quality: Dict[str, Any],
        context_assembly: Dict[str, Any],
        write_time_decisions: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on health metrics"""
        
        recommendations = []
        
        # Memory health recommendations
        if memory_health.get("status") == "critical":
            recommendations.append("Memory health is critical - review promotion criteria and gate thresholds")
        elif memory_health.get("status") == "warning":
            if memory_health.get("promotion_rate", 0) < 10:
                recommendations.append("Low memory promotion rate - consider reviewing promotion criteria")
            if memory_health.get("avg_confidence", 0) < 0.6:
                recommendations.append("Low promotion confidence - review content quality scoring")
        
        # Retrieval quality recommendations
        if retrieval_quality.get("status") == "critical":
            recommendations.append("Retrieval quality is critical - review embedding models and retrieval algorithms")
        elif retrieval_quality.get("status") == "warning":
            if retrieval_quality.get("avg_relevance", 0) < 0.6:
                recommendations.append("Low retrieval relevance - review semantic search parameters")
            if retrieval_quality.get("error_rate", 0) > 10:
                recommendations.append("High retrieval error rate - investigate provider issues")
        
        # Context assembly recommendations
        if context_assembly.get("status") == "critical":
            recommendations.append("Context assembly is critical - review layer processing and token allocation")
        elif context_assembly.get("status") == "warning":
            if context_assembly.get("avg_assembly_time", 0) > 500:
                recommendations.append("Slow context assembly - optimize layer processing performance")
            if context_assembly.get("redaction_rate", 0) > 25:
                recommendations.append("High redaction rate - review data filtering before assembly")
        
        # Decision system recommendations
        if write_time_decisions.get("status") == "warning":
            if write_time_decisions.get("avg_confidence", 0) < 0.6:
                recommendations.append("Low decision confidence - review classification accuracy")
        
        # Overall system recommendations
        overall_score = self._calculate_overall_health(
            memory_health, retrieval_quality, context_assembly, write_time_decisions
        )
        
        if overall_score < 50:
            recommendations.append("Overall system health is poor - comprehensive review needed")
        elif overall_score < 70:
            recommendations.append("System health needs attention - address warnings above")
        else:
            recommendations.append("System health is good - continue monitoring")
        
        return recommendations
    
    async def get_cached_metrics(
        self, 
        user_id: Optional[str] = None,
        time_window_hours: int = 24
    ) -> Optional[SystemMetrics]:
        """Get cached metrics if available and not expired"""
        
        cache_key = f"{user_id}:{time_window_hours}"
        if cache_key in self._metrics_cache:
            cached_data = self._metrics_cache[cache_key]
            if datetime.utcnow().timestamp() < cached_data["expires_at"]:
                return cached_data["metrics"]
        
        return None


# Global metrics collector instance
metrics_collector = MetricsCollector()