"""
Write-Time Intelligence (The Anti-Rot Layer) - Enhanced with Observability
Core Decision Matrix for message storage and processing decisions

The Prime Directive: Every decision affecting memory, retrieval, routing, or context
must be inspectable. No black boxes.
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
from ..observability.decision_logger import decision_logger
from ..observability.memory_logger import memory_logger

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
    """Result of write-time decision matrix with full observability"""
    message_type: MessageType
    actions: List[DecisionAction]
    confidence: float
    reasoning: str
    metadata: Dict[str, Any]
    should_block_write: bool = False
    # Observability fields
    correlation_id: Optional[str] = None
    decision_id: Optional[str] = None


class WriteTimeDecisionMatrix:
    """
    The core decision matrix that determines what happens to each message
    
    Enhanced with comprehensive observability for The Prime Directive compliance:
    - Every decision is logged with full context
    - Rate limiting decisions are traceable
    - Memory promotion events are tracked
    - Correlation IDs for end-to-end tracing
    
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
        }
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
        message_data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> WriteTimeDecision:
        """
        Apply the decision matrix to determine message fate WITH FULL OBSERVABILITY
        
        The Prime Directive: Every decision affecting memory, retrieval, routing, or context
        must be inspectable. No black boxes.
        
        Args:
            classification: Message classification result
            message_data: Message metadata and content
            correlation_id: For end-to-end tracing across services
        
        Returns:
            WriteTimeDecision with actions to take and full observability data
        """
        message_type = classification.message_type
        user_id = message_data.get("user_id")
        conversation_id = message_data.get("conversation_id")
        message_id = message_data.get("message_id")
        
        # Generate correlation ID if not provided
        if not correlation_id:
            correlation_id = f"writetime_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{message_id}"
        
        # Get decision rules for this message type
        rules = self.DECISION_TABLE.get(message_type, self.DECISION_TABLE[MessageType.CHAT])
        
        # LOG DECISION START - Prime Directive compliance
        logger.info(
            "Write-time decision matrix started",
            message_id=message_id,
            message_type=message_type.value,
            user_id=user_id,
            conversation_id=conversation_id,
            classification_confidence=classification.confidence,
            correlation_id=correlation_id,
            event_type="decision_matrix_started"
        )
        
        # Build actions list based on rules with full observability
        actions = []
        decision_factors = {
            "rules_applied": rules,
            "rate_limit_checks": {},
            "content_quality_checks": {}
        }
        
        # Check embedding decision
        if rules["embed"]:
            should_embed = self._should_embed(user_id, message_data)
            decision_factors["rate_limit_checks"]["embed"] = {
                "allowed": should_embed,
                "current_count": self._embedding_counts.get(user_id, {}).get(
                    datetime.utcnow().strftime("%Y-%m-%d-%H"), 0
                ),
                "max_allowed": self.MAX_EMBEDDINGS_PER_HOUR
            }
            
            if should_embed:
                actions.append(DecisionAction.EMBED)
                logger.info(
                    "Embedding decision: ALLOWED",
                    message_id=message_id,
                    user_id=user_id,
                    correlation_id=correlation_id,
                    event_type="embed_decision_allowed"
                )
            else:
                logger.warning(
                    "Embedding decision: BLOCKED by rate limit",
                    message_id=message_id,
                    user_id=user_id,
                    message_type=message_type.value,
                    correlation_id=correlation_id,
                    event_type="embed_decision_blocked",
                    reason="rate_limit_exceeded"
                )
        
        # Check summarization decision
        if rules["summarize"]:
            should_summarize = self._should_summarize(user_id)
            decision_factors["rate_limit_checks"]["summarize"] = {
                "allowed": should_summarize,
                "current_count": self._summary_counts.get(user_id, {}).get(
                    datetime.utcnow().strftime("%Y-%m-%d"), 0
                ),
                "max_allowed": self.MAX_SUMMARIES_PER_DAY
            }
            
            if should_summarize:
                actions.append(DecisionAction.SUMMARIZE)
                logger.info(
                    "Summarization decision: ALLOWED",
                    message_id=message_id,
                    user_id=user_id,
                    correlation_id=correlation_id,
                    event_type="summarize_decision_allowed"
                )
            else:
                logger.warning(
                    "Summarization decision: BLOCKED by rate limit",
                    message_id=message_id,
                    user_id=user_id,
                    message_type=message_type.value,
                    correlation_id=correlation_id,
                    event_type="summarize_decision_blocked",
                    reason="rate_limit_exceeded"
                )
        
        # Check caching decision
        if rules["cache"]:
            cache_duration = rules["cache"] if isinstance(rules["cache"], str) else "long"
            actions.append(DecisionAction.CACHE)
            message_data["cache_duration"] = cache_duration
            logger.info(
                "Caching decision: ALLOWED",
                message_id=message_id,
                cache_duration=cache_duration,
                correlation_id=correlation_id,
                event_type="cache_decision_allowed"
            )
        
        # Check discard decision
        if rules["discard"]:
            actions.append(DecisionAction.DISCARD)
            logger.info(
                "Discard decision: APPLIED",
                message_id=message_id,
                user_id=user_id,
                message_type=message_type.value,
                reasoning=rules["reasoning"],
                correlation_id=correlation_id,
                event_type="discard_decision_applied"
            )
        
        # Build decision result with observability data
        decision_id = f"decision_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        
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
                "timestamp": datetime.utcnow().isoformat(),
                "decision_factors": decision_factors
            },
            correlation_id=correlation_id,
            decision_id=decision_id
        )
        
        # LOG COMPLETE DECISION - Prime Directive compliance
        logger.info(
            "Write-time decision completed",
            message_id=message_id,
            message_type=message_type.value,
            decision_id=decision_id,
            actions=[action.value for action in actions],
            confidence=classification.confidence,
            reasoning=rules["reasoning"],
            user_id=user_id,
            correlation_id=correlation_id,
            event_type="decision_matrix_completed",
            prime_directive_compliant=True
        )
        
        # Record decision for observability
        decision_logger.record_decision(
            decision_id=decision_id,
            decision_type="write_time_matrix",
            context={
                "message_id": message_id,
                "message_type": message_type.value,
                "user_id": user_id,
                "conversation_id": conversation_id,
                "actions": [action.value for action in actions],
                "confidence": classification.confidence,
                "reasoning": rules["reasoning"],
                "classification": classification.reasoning,
                "rules_applied": rules,
                "decision_factors": decision_factors
            },
            correlation_id=correlation_id
        )
        
        return decision
    
    def _should_embed(self, user_id: Optional[str], message_data: Dict[str, Any]) -> bool:
        """Check if embedding should be allowed based on rate limits and content WITH TRACING"""
        if not user_id:
            return False
        
        # Check rate limits
        current_hour = datetime.utcnow().strftime("%Y-%m-%d-%H")
        hour_count = self._embedding_counts.get(user_id, {}).get(current_hour, 0)
        
        if hour_count >= self.MAX_EMBEDDINGS_PER_HOUR:
            return False
        
        # Check content quality (don't embed very short or empty content)
        content = message_data.get("content", "")
        content_length = len(content.strip())
        
        if content_length < 10:
            logger.info(
                "Embedding blocked by content quality",
                user_id=user_id,
                content_length=content_length,
                min_required=10,
                event_type="embed_content_quality_blocked"
            )
            return False
        
        # Update counter
        if user_id not in self._embedding_counts:
            self._embedding_counts[user_id] = {}
        self._embedding_counts[user_id][current_hour] = hour_count + 1
        
        return True
    
    def _should_summarize(self, user_id: Optional[str]) -> bool:
        """Check if summarization should be allowed based on rate limits WITH TRACING"""
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
        Execute the actions determined by the decision matrix WITH FULL OBSERVABILITY
        
        The Prime Directive: Every action execution must be traceable and inspectable.
        
        Args:
            decision: WriteTimeDecision with actions to execute
            message_data: Message data to process
        
        Returns:
            Execution results with full observability
        """
        message_id = message_data.get("message_id")
        correlation_id = decision.correlation_id
        
        results = {
            "message_id": message_id,
            "decision_id": decision.decision_id,
            "correlation_id": correlation_id,
            "actions_executed": [],
            "actions_failed": [],
            "execution_time": datetime.utcnow().isoformat(),
            "prime_directive_compliant": True
        }
        
        logger.info(
            "Decision execution started",
            message_id=message_id,
            decision_id=decision.decision_id,
            actions_to_execute=[action.value for action in decision.actions],
            correlation_id=correlation_id,
            event_type="decision_execution_started"
        )
        
        for action in decision.actions:
            try:
                if action == DecisionAction.EMBED:
                    await self._execute_embed(message_data, correlation_id)
                    results["actions_executed"].append("embed")
                    logger.info(
                        "Embed action executed successfully",
                        message_id=message_id,
                        correlation_id=correlation_id,
                        event_type="embed_action_completed"
                    )
                
                elif action == DecisionAction.SUMMARIZE:
                    await self._execute_summarize(message_data, correlation_id)
                    results["actions_executed"].append("summarize")
                    logger.info(
                        "Summarize action executed successfully",
                        message_id=message_id,
                        correlation_id=correlation_id,
                        event_type="summarize_action_completed"
                    )
                
                elif action == DecisionAction.CACHE:
                    await self._execute_cache(message_data, correlation_id)
                    results["actions_executed"].append("cache")
                    logger.info(
                        "Cache action executed successfully",
                        message_id=message_id,
                        correlation_id=correlation_id,
                        event_type="cache_action_completed"
                    )
                
                elif action == DecisionAction.DISCARD:
                    await self._execute_discard(message_data, correlation_id)
                    results["actions_executed"].append("discard")
                    logger.info(
                        "Discard action executed successfully",
                        message_id=message_id,
                        correlation_id=correlation_id,
                        event_type="discard_action_completed"
                    )
                    # Don't store if discarding
                    return results
                
                elif action == DecisionAction.STORE:
                    # Basic storage (for messages that pass decision matrix)
                    results["actions_executed"].append("store")
                    logger.info(
                        "Store action executed",
                        message_id=message_id,
                        correlation_id=correlation_id,
                        event_type="store_action_completed"
                    )
                
            except Exception as e:
                logger.error(
                    "Action execution failed",
                    action=action.value,
                    error=str(e),
                    message_id=message_id,
                    correlation_id=correlation_id,
                    event_type="action_execution_failed"
                )
                results["actions_failed"].append(action.value)
        
        # Always store the message if not discarded (for conversation history)
        if DecisionAction.DISCARD not in decision.actions:
            results["actions_executed"].append("store")
        
        logger.info(
            "Decision execution completed",
            message_id=message_id,
            decision_id=decision.decision_id,
            actions_executed=results["actions_executed"],
            actions_failed=results["actions_failed"],
            correlation_id=correlation_id,
            event_type="decision_execution_completed"
        )
        
        return results
    
    async def _execute_embed(self, message_data: Dict[str, Any], correlation_id: str):
        """Execute embedding action WITH OBSERVABILITY"""
        user_id = message_data.get("user_id")
        conversation_id = message_data.get("conversation_id")
        message_id = message_data.get("message_id")
        content = message_data.get("content", "")
        
        logger.info(
            "Starting embed action execution",
            message_id=message_id,
            user_id=user_id,
            content_length=len(content),
            correlation_id=correlation_id,
            event_type="embed_execution_started"
        )
        
        # Queue for async embedding
        await embedding_worker.queue_message_embedding(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            content=content,
            metadata=message_data.get("metadata", {})
        )
    
    async def _execute_summarize(self, message_data: Dict[str, Any], correlation_id: str):
        """Execute summarization action WITH OBSERVABILITY"""
        conversation_id = message_data.get("conversation_id")
        content = message_data.get("content", "")
        message_id = message_data.get("message_id")
        
        logger.info(
            "Starting summarize action execution",
            message_id=message_id,
            conversation_id=conversation_id,
            content_length=len(content),
            correlation_id=correlation_id,
            event_type="summarize_execution_started"
        )
        
        if conversation_id and content:
            # Queue for async summarization
            await embedding_worker.queue_summary_embedding(
                conversation_id=conversation_id,
                summary_text=content
            )
    
    async def _execute_cache(self, message_data: Dict[str, Any], correlation_id: str):
        """Execute caching action WITH OBSERVABILITY"""
        cache_duration = message_data.get("cache_duration", "short")
        message_id = message_data.get("message_id")
        content = message_data.get("content", "")