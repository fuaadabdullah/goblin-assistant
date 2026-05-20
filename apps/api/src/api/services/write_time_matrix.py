"""
Write-Time Intelligence (The Anti-Rot Layer)
Core Decision Matrix for message storage and processing decisions
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import structlog

from .message_classifier import MessageType, MessageClassification
from .embedding_service import embedding_worker
from .cache_service import cache_service
from .retrieval_service import retrieval_service as _retrieval_singleton
from .memory_promotion_service import memory_promotion_service
from .observability_service import observability_service

logger = structlog.get_logger()


class DecisionAction(Enum):
    """Actions that can be taken for each message type"""
    EMBED = "embed"
    SUMMARIZE = "summarize"
    CACHE = "cache"
    DISCARD = "discard"
    STORE = "store"


@dataclass
class WriteTimeDecision:
    """Result of write-time decision matrix"""
    message_type: MessageType
    actions: List[DecisionAction]
    confidence: float
    reasoning: str
    metadata: Dict[str, Any]
    should_block_write: bool = False


class WriteTimeDecisionMatrix:
    """
    The core decision matrix that determines what happens to each message
    
    Core Rule: Nothing gets stored without being judged.
    Every message passes through this matrix before touching:
    - embeddings
    - summaries  
    - cache
    - long-term storage
    """
    
    # Decision matrix table from requirements
    DECISION_TABLE = {
        MessageType.CHAT: {
            "embed": False,
            "summarize": False,
            "cache": "short",  # ⚠️ Short-term only
            "discard": False,
            "reasoning": "Chat messages are ephemeral, don't embed or summarize"
        },
        MessageType.TASK_RESULT: {
            "embed": True,
            "summarize": True,
            "cache": True,
            "discard": False,
            "reasoning": "Task results are valuable information worth summarizing"
        },
        MessageType.FACT: {
            "embed": True,
            "summarize": False,
            "cache": True,
            "discard": False,
            "reasoning": "Facts are declarative knowledge worth storing"
        },
        MessageType.PREFERENCE: {
            "embed": True,
            "summarize": False,
            "cache": True,
            "discard": False,
            "reasoning": "Preferences inform future interactions"
        },
        MessageType.SYSTEM: {
            "embed": False,
            "summarize": False,
            "cache": False,
            "discard": True,
            "reasoning": "System messages are operational, not conversational"
        },
        MessageType.NOISE: {
            "embed": False,
            "summarize": False,
            "cache": False,
            "discard": True,
            "reasoning": "Noise provides no value, should be discarded"
        },
        # Finance domain — all finance types get aggressive retention
        MessageType.FINANCIAL_ENTITY: {
            "embed": True,
            "summarize": False,
            "cache": True,
            "discard": False,
            "reasoning": "Financial entities (tickers, instruments, issuers) are durable domain knowledge"
        },
        MessageType.RISK_SIGNAL: {
            "embed": True,
            "summarize": True,
            "cache": True,
            "discard": False,
            "reasoning": "Risk metrics and signals inform portfolio decisions"
        },
        MessageType.REGULATORY_REF: {
            "embed": True,
            "summarize": False,
            "cache": True,
            "discard": False,
            "reasoning": "Regulatory references are compliance-critical long-term knowledge"
        },
        MessageType.PORTFOLIO_ACTION: {
            "embed": True,
            "summarize": True,
            "cache": True,
            "discard": False,
            "reasoning": "Portfolio actions document intent and constraints for audit trails"
        },
        MessageType.MACRO_EVENT: {
            "embed": True,
            "summarize": True,
            "cache": "short",
            "discard": False,
            "reasoning": "Macro events are time-sensitive but valuable for context windows"
        },
    }
    
    # Rate limiting guardrails
    MAX_EMBEDDINGS_PER_HOUR = 50
    MAX_SUMMARIES_PER_DAY = 10
    MAX_CACHE_SIZE_MB = 100
    
    def __init__(self):
        self.retrieval_service = _retrieval_singleton
        self._embedding_counts = {}  # user_id -> {hour: count}
        self._summary_counts = {}    # user_id -> {day: count}
    
    def apply_decision_matrix(
        self, 
        classification: MessageClassification,
        message_data: Dict[str, Any]
    ) -> WriteTimeDecision:
        """
        Apply the decision matrix to determine message fate
        
        Args:
            classification: Message classification result
            message_data: Message metadata and content
        
        Returns:
            WriteTimeDecision with actions to take
        """
        message_type = classification.message_type
        user_id = message_data.get("user_id")
        conversation_id = message_data.get("conversation_id")
        
        # Get decision rules for this message type
        rules = self.DECISION_TABLE.get(message_type, self.DECISION_TABLE[MessageType.CHAT])
        
        # Build actions list based on rules
        actions = []
        
        # Check embedding decision
        if rules["embed"]:
            if self._should_embed(user_id, message_data):
                actions.append(DecisionAction.EMBED)
            else:
                logger.warning(
                    "Embedding blocked by rate limit",
                    user_id=user_id,
                    message_type=message_type.value
                )
        
        # Check summarization decision
        if rules["summarize"]:
            if self._should_summarize(user_id):
                actions.append(DecisionAction.SUMMARIZE)
            else:
                logger.warning(
                    "Summarization blocked by rate limit",
                    user_id=user_id,
                    message_type=message_type.value
                )
        
        # Check caching decision
        if rules["cache"]:
            cache_duration = rules["cache"] if isinstance(rules["cache"], str) else "long"
            actions.append(DecisionAction.CACHE)
            message_data["cache_duration"] = cache_duration
        
        # Check discard decision
        if rules["discard"]:
            actions.append(DecisionAction.DISCARD)
            logger.info(
                "Message marked for discard",
                user_id=user_id,
                message_type=message_type.value,
                reasoning=rules["reasoning"]
            )
        
        # Build decision result
        decision = WriteTimeDecision(
            message_type=message_type,
            actions=actions,
            confidence=classification.confidence,
            reasoning=rules["reasoning"],
            metadata={
                "original_classification": classification.reasoning,
                "decision_rules": rules,
                "user_id": user_id,
                "conversation_id": conversation_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            "Write-time decision made",
            message_type=message_type.value,
            actions=[action.value for action in actions],
            confidence=classification.confidence,
            user_id=user_id
        )
        
        # Log decision to observability system
        try:
            observability_service.log_write_time_decision(
                message_id=message_data.get("message_id"),
                user_id=user_id,
                conversation_id=conversation_id,
                message_content=message_data.get("content", ""),
                message_role=message_data.get("role", ""),
                write_time_result={
                    "classification": {
                        "type": classification.message_type.value,
                        "confidence": classification.confidence,
                        "reasoning": classification.reasoning
                    },
                    "decision": {
                        "actions": decision.actions,
                        "reasoning": decision.reasoning,
                        "confidence": decision.confidence
                    },
                    "execution": {}
                },
                request_id=message_data.get("request_id")
            )
        except Exception as e:
            logger.error("Failed to log write-time decision to observability", error=str(e))
        
        return decision
    
    def _should_embed(self, user_id: Optional[str], message_data: Dict[str, Any]) -> bool:
        """Check if embedding should be allowed based on rate limits and content"""
        if not user_id:
            return False
        
        # Check rate limits
        current_hour = datetime.utcnow().strftime("%Y-%m-%d-%H")
        hour_count = self._embedding_counts.get(user_id, {}).get(current_hour, 0)
        
        if hour_count >= self.MAX_EMBEDDINGS_PER_HOUR:
            return False
        
        # Check content quality (don't embed very short or empty content)
        content = message_data.get("content", "")
        if len(content.strip()) < 10:
            return False
        
        # Update counter
        if user_id not in self._embedding_counts:
            self._embedding_counts[user_id] = {}
        self._embedding_counts[user_id][current_hour] = hour_count + 1
        
        return True
    
    def _should_summarize(self, user_id: Optional[str]) -> bool:
        """Check if summarization should be allowed based on rate limits"""
        if not user_id:
            return False
        
        current_day = datetime.utcnow().strftime("%Y-%m-%d")
        day_count = self._summary_counts.get(user_id, {}).get(current_day, 0)
        
        if day_count >= self.MAX_SUMMARIES_PER_DAY:
            return False
        
        # Update counter
        if user_id not in self._summary_counts:
            self._summary_counts[user_id] = {}
        self._summary_counts[user_id][current_day] = day_count + 1
        
        return True
    
    async def execute_decision(
        self, 
        decision: WriteTimeDecision, 
        message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the actions determined by the decision matrix
        
        Args:
            decision: WriteTimeDecision with actions to execute
            message_data: Message data to process
        
        Returns:
            Execution results
        """
        results = {
            "message_id": message_data.get("message_id"),
            "actions_executed": [],
            "actions_failed": [],
            "execution_time": datetime.utcnow().isoformat()
        }
        
        for action in decision.actions:
            try:
                if action == DecisionAction.EMBED:
                    await self._execute_embed(message_data)
                    results["actions_executed"].append("embed")
                
                elif action == DecisionAction.SUMMARIZE:
                    await self._execute_summarize(message_data)
                    results["actions_executed"].append("summarize")
                
                elif action == DecisionAction.CACHE:
                    await self._execute_cache(message_data)
                    results["actions_executed"].append("cache")
                
                elif action == DecisionAction.DISCARD:
                    await self._execute_discard(message_data)
                    results["actions_executed"].append("discard")
                    # Don't store if discarding
                    return results
                
                elif action == DecisionAction.STORE:
                    # Basic storage (for messages that pass decision matrix)
                    results["actions_executed"].append("store")
                
            except Exception as e:
                logger.error(
                    "Action execution failed",
                    action=action.value,
                    error=str(e),
                    message_id=message_data.get("message_id")
                )
                results["actions_failed"].append(action.value)
        
        # Always store the message if not discarded (for conversation history)
        if DecisionAction.DISCARD not in decision.actions:
            results["actions_executed"].append("store")
        
        return results
    
    async def _execute_embed(self, message_data: Dict[str, Any]):
        """Execute embedding action"""
        user_id = message_data.get("user_id")
        conversation_id = message_data.get("conversation_id")
        message_id = message_data.get("message_id")
        content = message_data.get("content", "")
        
        # Queue for async embedding
        await embedding_worker.queue_message_embedding(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            content=content,
            metadata=message_data.get("metadata", {})
        )
    
    async def _execute_summarize(self, message_data: Dict[str, Any]):
        """Execute summarization action"""
        conversation_id = message_data.get("conversation_id")
        content = message_data.get("content", "")
        
        if conversation_id and content:
            # Queue for async summarization
            await embedding_worker.queue_summary_embedding(
                conversation_id=conversation_id,
                summary_text=content
            )
    
    async def _execute_cache(self, message_data: Dict[str, Any]):
        """Execute caching action"""
        cache_duration = message_data.get("cache_duration", "short")
        message_id = message_data.get("message_id")
        content = message_data.get("content", "")
        
        if cache_duration == "short":
            ttl = 300  # 5 minutes
        elif cache_duration == "long":
            ttl = 3600  # 1 hour
        else:
            ttl = 600  # 10 minutes default
        
        await cache_service.set(
            key=f"message:{message_id}",
            value=message_data,
            ttl=ttl
        )
    
    async def _execute_discard(self, message_data: Dict[str, Any]):
        """Execute discard action - log but don't store"""
        message_id = message_data.get("message_id")
        content_preview = message_data.get("content", "")[:50]
        
        logger.info(
            "Message discarded (rot prevention)",
            message_id=message_id,
            content_preview=content_preview,
            reason="Noise or system message"
        )
        
        # Log for observability but don't store
        # This could be sent to monitoring systems for analysis


class WriteTimeIntelligence:
    """Main service for Write-Time Intelligence integration"""
    
    def __init__(self):
        self.decision_matrix = WriteTimeDecisionMatrix()
    
    async def process_message(
        self,
        message_id: str,
        content: str,
        role: str,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete write-time processing pipeline
        
        Args:
            message_id: Unique message identifier
            content: Message content
            role: Message role (user/assistant/system)
            user_id: User identifier
            conversation_id: Conversation identifier
            metadata: Additional message metadata
        
        Returns:
            Processing results with decisions and execution status
        """
        # Build message data
        message_data = {
            "message_id": message_id,
            "content": content,
            "role": role,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Import here to avoid circular imports
        from .message_classifier import classification_pipeline
        
        # Step 1: Classify message
        classification_result = await classification_pipeline.process_message(
            message_id=message_id,
            content=content,
            role=role,
            conversation_id=conversation_id,
            user_id=user_id
        )
        
        # Convert to MessageClassification object
        from .message_classifier import MessageClassification
        classification = MessageClassification(
            message_type=MessageType(classification_result["classification"]["type"]),
            confidence=classification_result["classification"]["confidence"],
            keywords=classification_result["classification"]["keywords"],
            reasoning=classification_result["classification"]["reasoning"],
            metadata=classification_result["metadata"]
        )
        
        # Step 2: Apply decision matrix
        decision = self.decision_matrix.apply_decision_matrix(
            classification=classification,
            message_data=message_data
        )
        
        # Step 3: Execute decisions
        execution_results = await self.decision_matrix.execute_decision(
            decision=decision,
            message_data=message_data
        )
        
        # Step 4: Handle memory promotion for summaries
        promotion_results = []
        if decision.actions and any(action.value == "summarize" for action in decision.actions):
            promotion_results = await self._handle_memory_promotion(
                summary_text=content,
                conversation_id=conversation_id,
                user_id=user_id
            )
        
        # Build final result
        result = {
            "message_id": message_id,
            "classification": {
                "type": classification.message_type.value,
                "confidence": classification.confidence,
                "reasoning": classification.reasoning
            },
            "decision": {
                "actions": [action.value for action in decision.actions],
                "reasoning": decision.reasoning,
                "confidence": decision.confidence
            },
            "execution": execution_results,
            "memory_promotion": promotion_results,
            "processed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(
            "Write-time processing completed",
            message_id=message_id,
            message_type=classification.message_type.value,
            actions_executed=execution_results["actions_executed"],
            memory_promotions=len(promotion_results)
        )
        
        return result
    
    async def _handle_memory_promotion(
        self,
        summary_text: str,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Handle memory promotion from conversation summaries"""
        try:
            # Use memory promotion service to evaluate summary for long-term memory
            promotion_results = await memory_promotion_service.promote_from_summary(
                summary_text=summary_text,
                conversation_id=conversation_id,
                user_id=user_id
            )
            
            # Convert to serializable format
            result_dicts = []
            for result in promotion_results:
                result_dicts.append({
                    "promoted": result.promoted,
                    "gates_passed": [gate.value for gate in result.gates_passed],
                    "gates_failed": [gate.value for gate in result.gates_failed],
                    "reason": result.reason,
                    "memory_fact_id": result.memory_fact_id
                })
            
            logger.info(
                "Memory promotion completed",
                conversation_id=conversation_id,
                user_id=user_id,
                promoted_count=sum(1 for r in promotion_results if r.promoted),
                total_candidates=len(promotion_results)
            )
            
            return result_dicts
            
        except Exception as e:
            logger.error(
                "Memory promotion failed",
                conversation_id=conversation_id,
                user_id=user_id,
                error=str(e)
            )
            return []


# Global instance
write_time_intelligence = WriteTimeIntelligence()