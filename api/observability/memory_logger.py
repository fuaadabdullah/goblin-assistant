"""
Memory Promotion Logging System
Tracks all memory promotion events with full audit trail and debugging capabilities
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import structlog

from ..config.system_config import get_system_config

logger = structlog.get_logger()


class PromotionGate(Enum):
    """Promotion gates that must be passed for memory promotion"""
    REPETITION = "repetition"
    TIME_SPAN = "time_span"
    STABILITY = "stability"
    CONTENT_QUALITY = "content_quality"


@dataclass
class MemoryPromotionEvent:
    """Complete record of a memory promotion attempt"""
    event_id: str
    timestamp: datetime
    candidate_text: str
    category: str
    source_conversation: str
    source_type: str
    confidence_score: float
    promotion_decision: bool
    gates_passed: List[PromotionGate]
    gates_failed: List[PromotionGate]
    rejection_reason: Optional[str]
    memory_fact_id: Optional[str]
    user_id: Optional[str]
    request_id: Optional[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["gates_passed"] = [gate.value for gate in self.gates_passed]
        data["gates_failed"] = [gate.value for gate in self.gates_failed]
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string for structured logging"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class MemoryPromotionLogger:
    """Centralized logging for memory promotion events"""
    
    def __init__(self):
        self.config = get_system_config()
        self._promotion_cache = {}  # Cache recent promotions for debugging
    
    async def log_promotion_attempt(
        self,
        candidate_text: str,
        category: str,
        source_conversation: str,
        source_type: str,
        confidence_score: float,
        promotion_decision: bool,
        gates_passed: List[PromotionGate],
        gates_failed: List[PromotionGate],
        rejection_reason: Optional[str],
        memory_fact_id: Optional[str],
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryPromotionEvent:
        """Log a memory promotion attempt with full context"""
        
        event = MemoryPromotionEvent(
            event_id=f"prom_{int(datetime.utcnow().timestamp())}_{hash(candidate_text) % 10000}",
            timestamp=datetime.utcnow(),
            candidate_text=candidate_text,
            category=category,
            source_conversation=source_conversation,
            source_type=source_type,
            confidence_score=confidence_score,
            promotion_decision=promotion_decision,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
            rejection_reason=rejection_reason,
            memory_fact_id=memory_fact_id,
            user_id=user_id,
            request_id=request_id,
            metadata=metadata or {}
        )
        
        # Store in cache for debugging
        cache_key = f"{source_conversation}:{hash(candidate_text) % 10000}"
        self._promotion_cache[cache_key] = event
        
        # Log with structured format
        self._log_promotion_structured(event)
        
        # Log to file if configured
        if self.config.get("observability", {}).get("log_promotions_to_file", False):
            await self._log_to_file(event)
        
        return event
    
    def _log_promotion_structured(self, event: MemoryPromotionEvent):
        """Log promotion event with structured format for observability"""
        
        # Create structured log entry
        log_data = {
            "observability_event": True,
            "event_type": "memory_promotion",
            "promotion_event": {
                "event_id": event.event_id,
                "decision": "promoted" if event.promotion_decision else "rejected",
                "category": event.category,
                "confidence_score": event.confidence_score,
                "candidate_preview": event.candidate_text[:100] + "..." if len(event.candidate_text) > 100 else event.candidate_text,
                "source": {
                    "conversation": event.source_conversation,
                    "type": event.source_type
                },
                "gates": {
                    "passed": [gate.value for gate in event.gates_passed],
                    "failed": [gate.value for gate in event.gates_failed]
                },
                "rejection_reason": event.rejection_reason,
                "memory_fact_id": event.memory_fact_id
            },
            "context": {
                "user_id": event.user_id,
                "request_id": event.request_id,
                "timestamp": event.timestamp.isoformat()
            },
            "metadata": event.metadata
        }
        
        # Log based on promotion outcome
        if event.promotion_decision:
            logger.info(f"PROMOTION: Memory fact promoted", extra={"promotion": log_data})
        else:
            logger.warning(f"PROMOTION: Memory fact rejected", extra={"promotion": log_data})
    
    async def _log_to_file(self, event: MemoryPromotionEvent):
        """Log promotion event to file for persistent storage"""
        try:
            log_file = self.config.get("observability", {}).get("promotion_log_file", "promotions.log")
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(event.to_json() + "\n")
                
        except Exception as e:
            logger.error(f"Failed to log promotion to file: {e}")
    
    async def get_promotion_history(
        self, 
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get promotion history with filtering"""
        
        # Filter events by user and conversation
        events = []
        for event in self._promotion_cache.values():
            if user_id and event.user_id != user_id:
                continue
            if conversation_id and event.source_conversation != conversation_id:
                continue
            events.append(event.to_dict())
        
        # Sort by timestamp and limit
        events.sort(key=lambda x: x["timestamp"], reverse=True)
        return events[:limit]
    
    async def get_promotion_stats(
        self, 
        user_id: Optional[str] = None,
        time_window_hours: int = 24,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get promotion statistics for monitoring"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        # Filter events by time window, user, and category
        relevant_events = []
        for event in self._promotion_cache.values():
            if event.timestamp >= cutoff_time:
                if user_id is None or event.user_id == user_id:
                    if category is None or event.category == category:
                        relevant_events.append(event)
        
        if not relevant_events:
            return {
                "total_attempts": 0,
                "time_window_hours": time_window_hours,
                "user_id": user_id,
                "category": category
            }
        
        # Calculate statistics
        total = len(relevant_events)
        promoted = sum(1 for e in relevant_events if e.promotion_decision)
        rejected = total - promoted
        
        # Category distribution
        category_counts = {}
        for event in relevant_events:
            cat = event.category
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Gate analysis
        gates_passed_counts = {}
        gates_failed_counts = {}
        for event in relevant_events:
            for gate in event.gates_passed:
                gates_passed_counts[gate.value] = gates_passed_counts.get(gate.value, 0) + 1
            for gate in event.gates_failed:
                gates_failed_counts[gate.value] = gates_failed_counts.get(gate.value, 0) + 1
        
        # Rejection reasons
        rejection_reasons = {}
        for event in relevant_events:
            if not event.promotion_decision and event.rejection_reason:
                reason = event.rejection_reason
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
        
        return {
            "total_attempts": total,
            "promoted": promoted,
            "rejected": rejected,
            "promotion_rate": round((promoted / total * 100), 2) if total > 0 else 0,
            "time_window_hours": time_window_hours,
            "user_id": user_id,
            "category": category,
            "category_distribution": category_counts,
            "gate_analysis": {
                "gates_passed": gates_passed_counts,
                "gates_failed": gates_failed_counts
            },
            "rejection_reasons": rejection_reasons,
            "avg_confidence": {
                "promoted": round(sum(e.confidence_score for e in relevant_events if e.promotion_decision) / max(1, promoted), 2),
                "rejected": round(sum(e.confidence_score for e in relevant_events if not e.promotion_decision) / max(1, rejected), 2)
            }
        }
    
    async def get_memory_health_report(
        self, 
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive memory health report"""
        
        # Get all events for user
        user_events = []
        for event in self._promotion_cache.values():
            if user_id is None or event.user_id == user_id:
                user_events.append(event)
        
        if not user_events:
            return {
                "user_id": user_id,
                "status": "no_data",
                "message": "No memory promotion events found"
            }
        
        # Calculate health metrics
        total_attempts = len(user_events)
        promoted_count = sum(1 for e in user_events if e.promotion_decision)
        rejected_count = total_attempts - promoted_count
        
        # Check for contradictions (same content promoted with different categories)
        content_categories = {}
        contradictions = []
        for event in user_events:
            if event.promotion_decision:
                content_hash = hash(event.candidate_text)
                if content_hash in content_categories:
                    if content_categories[content_hash] != event.category:
                        contradictions.append({
                            "content_preview": event.candidate_text[:50],
                            "previous_category": content_categories[content_hash],
                            "current_category": event.category
                        })
                else:
                    content_categories[content_hash] = event.category
        
        # Analyze gate failure patterns
        gate_failures = {}
        for event in user_events:
            if not event.promotion_decision:
                for gate in event.gates_failed:
                    gate_failures[gate.value] = gate_failures.get(gate.value, 0) + 1
        
        # Determine health status
        contradiction_rate = len(contradictions) / max(1, promoted_count) * 100
        if contradiction_rate > 5:
            health_status = "critical"
        elif contradiction_rate > 2:
            health_status = "warning"
        elif rejected_count / max(1, total_attempts) > 0.8:
            health_status = "warning"
        else:
            health_status = "healthy"
        
        return {
            "user_id": user_id,
            "health_status": health_status,
            "metrics": {
                "total_promotion_attempts": total_attempts,
                "successful_promotions": promoted_count,
                "promotion_rejection_rate": round(rejected_count / max(1, total_attempts) * 100, 2),
                "contradiction_count": len(contradictions),
                "contradiction_rate": round(contradiction_rate, 2),
                "gate_failure_patterns": gate_failures
            },
            "contradictions": contradictions[:10],  # Show first 10 contradictions
            "recommendations": self._generate_health_recommendations(
                contradiction_rate, rejected_count, total_attempts, gate_failures
            )
        }
    
    def _generate_health_recommendations(
        self, 
        contradiction_rate: float, 
        rejected_count: int, 
        total_attempts: int,
        gate_failures: Dict[str, int]
    ) -> List[str]:
        """Generate recommendations based on memory health metrics"""
        
        recommendations = []
        
        if contradiction_rate > 5:
            recommendations.append("High contradiction rate detected - review memory promotion criteria")
        
        if rejected_count / max(1, total_attempts) > 0.8:
            recommendations.append("High rejection rate - consider adjusting promotion thresholds")
        
        if gate_failures.get("content_quality", 0) > gate_failures.get("repetition", 0):
            recommendations.append("Content quality gate failing frequently - review content quality filters")
        
        if gate_failures.get("stability", 0) > gate_failures.get("repetition", 0):
            recommendations.append("Stability gate failing frequently - review stability scoring")
        
        if not recommendations:
            recommendations.append("Memory health looks good - continue monitoring")
        
        return recommendations
    
    async def search_promotions(
        self,
        query: str,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        category: Optional[str] = None,
        promoted_only: bool = False,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Search promotions with advanced filtering"""
        
        results = []
        
        for event in self._promotion_cache.values():
            # Apply filters
            if user_id and event.user_id != user_id:
                continue
            if conversation_id and event.source_conversation != conversation_id:
                continue
            if category and event.category != category:
                continue
            if promoted_only and not event.promotion_decision:
                continue
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue
            
            # Apply text search
            if query:
                event_text = f"{event.candidate_text} {event.category} {event.rejection_reason or ''}"
                if query.lower() not in event_text.lower():
                    continue
            
            results.append(event.to_dict())
        
        # Sort by timestamp
        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results


# Global memory promotion logger instance
memory_promotion_logger = MemoryPromotionLogger()


async def log_memory_promotion(
    candidate_text: str,
    category: str,
    source_conversation: str,
    source_type: str,
    confidence_score: float,
    promotion_decision: bool,
    gates_passed: List[PromotionGate],
    gates_failed: List[PromotionGate],
    rejection_reason: Optional[str],
    memory_fact_id: Optional[str],
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> MemoryPromotionEvent:
    """Convenience function to log memory promotion events"""
    return await memory_promotion_logger.log_promotion_attempt(
        candidate_text=candidate_text,
        category=category,
        source_conversation=source_conversation,
        source_type=source_type,
        confidence_score=confidence_score,
        promotion_decision=promotion_decision,
        gates_passed=gates_passed,
        gates_failed=gates_failed,
        rejection_reason=rejection_reason,
        memory_fact_id=memory_fact_id,
        user_id=user_id,
        request_id=request_id,
        metadata=metadata
    )