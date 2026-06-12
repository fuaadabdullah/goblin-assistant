"""
Write-Time Intelligence (The Anti-Rot Layer)
Orchestrating service over the write-time decision matrix.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from .memory_promotion import memory_promotion_service
from .message_classifier import MessageClassification, MessageType
from .write_time_decision_matrix import (  # noqa: F401 — re-exported for backward compat
    DecisionAction,
    WriteTimeDecision,
    WriteTimeDecisionMatrix,
)

logger = structlog.get_logger()


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
        metadata: Optional[Dict[str, Any]] = None,
        intent: Optional[Any] = None,
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
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Import here to avoid circular imports
        from .message_classifier import classification_pipeline

        # Step 1: Classify message
        classification_result = await classification_pipeline.process_message(
            message_id=message_id,
            content=content,
            role=role,
            conversation_id=conversation_id,
            user_id=user_id,
        )

        # Convert to MessageClassification object

        classification = MessageClassification(
            message_type=MessageType(classification_result["classification"]["type"]),
            confidence=classification_result["classification"]["confidence"],
            keywords=classification_result["classification"]["keywords"],
            reasoning=classification_result["classification"]["reasoning"],
            metadata=classification_result["metadata"],
        )

        # Step 2: Apply decision matrix
        decision = self.decision_matrix.apply_decision_matrix(
            classification=classification, message_data=message_data, intent=intent
        )

        # Step 3: Execute decisions
        execution_results = await self.decision_matrix.execute_decision(
            decision=decision, message_data=message_data
        )

        # Step 4: Handle memory promotion for summaries
        promotion_results = []
        if decision.actions and any(action.value == "summarize" for action in decision.actions):
            promotion_results = await self._handle_memory_promotion(
                summary_text=content, conversation_id=conversation_id, user_id=user_id
            )

        # Build final result
        result = {
            "message_id": message_id,
            "classification": {
                "type": classification.message_type.value,
                "confidence": classification.confidence,
                "reasoning": classification.reasoning,
            },
            "decision": {
                "actions": [action.value for action in decision.actions],
                "reasoning": decision.reasoning,
                "confidence": decision.confidence,
            },
            "execution": execution_results,
            "memory_promotion": promotion_results,
            "processed_at": datetime.utcnow().isoformat(),
        }

        logger.info(
            "Write-time processing completed",
            message_id=message_id,
            message_type=classification.message_type.value,
            actions_executed=execution_results["actions_executed"],
            memory_promotions=len(promotion_results),
        )

        return result

    async def _handle_memory_promotion(
        self, summary_text: str, conversation_id: str, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Handle memory promotion from conversation summaries"""
        try:
            # Use memory promotion service to evaluate summary for long-term memory
            promotion_results = await memory_promotion_service.promote_from_summary(
                summary_text=summary_text,
                conversation_id=conversation_id,
                user_id=user_id,
            )

            # Convert to serializable format
            result_dicts = []
            for result in promotion_results:
                result_dicts.append(
                    {
                        "promoted": result.promoted,
                        "gates_passed": [gate.value for gate in result.gates_passed],
                        "gates_failed": [gate.value for gate in result.gates_failed],
                        "reason": result.reason,
                        "memory_fact_id": result.memory_fact_id,
                    }
                )

            logger.info(
                "Memory promotion completed",
                conversation_id=conversation_id,
                user_id=user_id,
                promoted_count=sum(1 for r in promotion_results if r.promoted),
                total_candidates=len(promotion_results),
            )

            return result_dicts

        except Exception as e:
            logger.error(
                "Memory promotion failed",
                conversation_id=conversation_id,
                user_id=user_id,
                error=str(e),
            )
            return []


# Global instance
write_time_intelligence = WriteTimeIntelligence()
