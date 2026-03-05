"""
Decision Logging System
Implements structured logging for write-time decisions with correlation IDs
"""

import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from uuid import uuid4
import structlog

from ..config.system_config import get_system_config

logger = structlog.get_logger()


class DecisionReason(Enum):
    """Reason codes for write-time decisions"""
    SHORT_CHAT = "short_chat"
    DECLARATIVE_FACT = "declarative_fact"
    TASK_RESULT = "task_result"
    LOW_SIGNAL = "low_signal"
    SYSTEM_MESSAGE = "system_message"
    NOISE = "noise"
    PREFERENCE = "preference"
    IDENTITY_TRAIT = "identity_trait"


@dataclass
class DecisionRecord:
    """Structured decision record for write-time decisions"""
    message_id: str
    conversation_id: str
    user_id: Optional[str]
    timestamp: datetime
    classified_type: str
    embedded: bool
    summarized: bool
    cached: bool
    discarded: bool
    reason_codes: List[DecisionReason]
    confidence: float
    decision_metadata: Dict[str, Any]
    processing_time_ms: float
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["reason_codes"] = [reason.value for reason in self.reason_codes]
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string for structured logging"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class DecisionLogger:
    """Centralized decision logging with correlation and structured output"""
    
    def __init__(self):
        self.config = get_system_config()
        self._decision_cache = {}  # Cache recent decisions for debugging
    
    async def log_decision(
        self,
        message_id: str,
        conversation_id: str,
        user_id: Optional[str],
        classified_type: str,
        embedded: bool,
        summarized: bool,
        cached: bool,
        discarded: bool,
        reason_codes: List[DecisionReason],
        confidence: float,
        decision_metadata: Dict[str, Any],
        processing_time_ms: float,
        request_id: Optional[str] = None
    ) -> DecisionRecord:
        """Log a write-time decision with full context"""
        
        decision = DecisionRecord(
            message_id=message_id,
            conversation_id=conversation_id,
            user_id=user_id,
            timestamp=datetime.utcnow(),
            classified_type=classified_type,
            embedded=embedded,
            summarized=summarized,
            cached=cached,
            discarded=discarded,
            reason_codes=reason_codes,
            confidence=confidence,
            decision_metadata=decision_metadata,
            processing_time_ms=processing_time_ms,
            request_id=request_id
        )
        
        # Store in cache for debugging
        cache_key = f"{conversation_id}:{message_id}"
        self._decision_cache[cache_key] = decision
        
        # Log with structured format
        self._log_decision_structured(decision)
        
        # Log to file if configured
        if self.config.get("observability", {}).get("log_decisions_to_file", False):
            await self._log_to_file(decision)
        
        return decision
    
    def _log_decision_structured(self, decision: DecisionRecord):
        """Log decision with structured format for observability"""
        
        # Create structured log entry
        log_data = {
            "observability_event": True,
            "event_type": "write_time_decision",
            "message_id": decision.message_id,
            "conversation_id": decision.conversation_id,
            "user_id": decision.user_id,
            "timestamp": decision.timestamp.isoformat(),
            "classification": {
                "type": decision.classified_type,
                "confidence": decision.confidence,
                "reason_codes": [reason.value for reason in decision.reason_codes]
            },
            "decisions": {
                "embedded": decision.embedded,
                "summarized": decision.summarized,
                "cached": decision.cached,
                "discarded": decision.discarded
            },
            "performance": {
                "processing_time_ms": decision.processing_time_ms,
                "request_id": decision.request_id
            },
            "metadata": decision.decision_metadata
        }
        
        # Log based on decision outcome
        if decision.discarded:
            logger.info(f"DECISION: Message discarded", extra={"decision": log_data})
        elif decision.embedded or decision.summarized:
            logger.info(f"DECISION: Message processed", extra={"decision": log_data})
        else:
            logger.debug(f"DECISION: Message stored only", extra={"decision": log_data})
    
    async def _log_to_file(self, decision: DecisionRecord):
        """Log decision to file for persistent storage"""
        try:
            log_file = self.config.get("observability", {}).get("decision_log_file", "decisions.log")
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(decision.to_json() + "\n")
                
        except Exception as e:
            logger.error(f"Failed to log decision to file: {e}")
    
    async def get_decision_history(
        self, 
        conversation_id: str, 
        limit: int = 100,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get decision history for a conversation"""
        
        # Filter decisions by conversation and user
        decisions = []
        for key, decision in self._decision_cache.items():
            if decision.conversation_id == conversation_id:
                if user_id is None or decision.user_id == user_id:
                    decisions.append(decision.to_dict())
        
        # Sort by timestamp and limit
        decisions.sort(key=lambda x: x["timestamp"], reverse=True)
        return decisions[:limit]
    
    async def get_decision_stats(
        self, 
        user_id: Optional[str] = None,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Get decision statistics for monitoring"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        # Filter decisions by time window and user
        relevant_decisions = []
        for decision in self._decision_cache.values():
            if decision.timestamp >= cutoff_time:
                if user_id is None or decision.user_id == user_id:
                    relevant_decisions.append(decision)
        
        if not relevant_decisions:
            return {
                "total_decisions": 0,
                "time_window_hours": time_window_hours,
                "user_id": user_id
            }
        
        # Calculate statistics
        total = len(relevant_decisions)
        
        # Classification stats
        classification_counts = {}
        for decision in relevant_decisions:
            cls = decision.classified_type
            classification_counts[cls] = classification_counts.get(cls, 0) + 1
        
        # Decision outcome stats
        outcomes = {
            "embedded": sum(1 for d in relevant_decisions if d.embedded),
            "summarized": sum(1 for d in relevant_decisions if d.summarized),
            "cached": sum(1 for d in relevant_decisions if d.cached),
            "discarded": sum(1 for d in relevant_decisions if d.discarded)
        }
        
        # Average confidence
        avg_confidence = sum(d.confidence for d in relevant_decisions) / total
        
        return {
            "total_decisions": total,
            "time_window_hours": time_window_hours,
            "user_id": user_id,
            "classification_stats": classification_counts,
            "outcome_stats": outcomes,
            "avg_confidence": round(avg_confidence, 2),
            "processing_time_stats": {
                "avg_ms": round(sum(d.processing_time_ms for d in relevant_decisions) / total, 2),
                "min_ms": min(d.processing_time_ms for d in relevant_decisions),
                "max_ms": max(d.processing_time_ms for d in relevant_decisions)
            }
        }
    
    async def search_decisions(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        classification_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Search decisions with advanced filtering"""
        
        results = []
        
        for decision in self._decision_cache.values():
            # Apply filters
            if conversation_id and decision.conversation_id != conversation_id:
                continue
            if user_id and decision.user_id != user_id:
                continue
            if classification_type and decision.classified_type != classification_type:
                continue
            if start_time and decision.timestamp < start_time:
                continue
            if end_time and decision.timestamp > end_time:
                continue
            
            # Apply text search
            if query:
                decision_text = f"{decision.classified_type} {decision.decision_metadata}"
                if query.lower() not in decision_text.lower():
                    continue
            
            results.append(decision.to_dict())
        
        # Sort by timestamp
        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results


# Global decision logger instance
decision_logger = DecisionLogger()


async def log_write_time_decision(
    message_id: str,
    conversation_id: str,
    user_id: Optional[str],
    classified_type: str,
    embedded: bool,
    summarized: bool,
    cached: bool,
    discarded: bool,
    reason_codes: List[DecisionReason],
    confidence: float,
    decision_metadata: Dict[str, Any],
    processing_time_ms: float,
    request_id: Optional[str] = None
) -> DecisionRecord:
    """Convenience function to log write-time decisions"""
    return await decision_logger.log_decision(
        message_id=message_id,
        conversation_id=conversation_id,
        user_id=user_id,
        classified_type=classified_type,
        embedded=embedded,
        summarized=summarized,
        cached=cached,
        discarded=discarded,
        reason_codes=reason_codes,
        confidence=confidence,
        decision_metadata=decision_metadata,
        processing_time_ms=processing_time_ms,
        request_id=request_id
    )