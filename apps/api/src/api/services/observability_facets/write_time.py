from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from ...observability.decision_logger import DecisionReason as ObsDecisionReason
from ...observability.decision_logger import decision_logger
from ..observability_models import DecisionReason

logger = structlog.get_logger()


class WriteTimeFacet:
    def __init__(self, owner: Any):
        self._owner = owner

    def _determine_reason_codes(
        self,
        message_content: str,
        message_role: str,
        classification: Dict[str, Any],
        decision: Dict[str, Any],
    ) -> List[str]:
        reason_codes = []

        if message_role == "system":
            reason_codes.append(DecisionReason.SYSTEM_MESSAGE.value)
        elif message_role == "user":
            if len(message_content) < 10:
                reason_codes.append(DecisionReason.SHORT_CHAT.value)
            else:
                reason_codes.append(DecisionReason.CONTEXT_RELEVANT.value)

        message_type = classification.get("type", "")
        if message_type == "fact":
            reason_codes.append(DecisionReason.DECLARATIVE_FACT.value)
        elif message_type == "task_result":
            reason_codes.append(DecisionReason.TASK_RESULT.value)
        elif message_type == "noise":
            reason_codes.append(DecisionReason.NOISE.value)
        elif message_type == "preference":
            reason_codes.append(DecisionReason.USER_PREFERENCE.value)

        actions = [action.value for action in decision.get("actions", [])]
        if "embed" in actions:
            reason_codes.append(DecisionReason.CONTEXT_RELEVANT.value)
        if "discard" in actions:
            reason_codes.append(DecisionReason.LOW_SIGNAL.value)

        return list(set(reason_codes))

    def log_write_time_decision(
        self,
        message_id: str,
        user_id: Optional[str],
        conversation_id: Optional[str],
        message_content: str,
        message_role: str,
        write_time_result: Dict[str, Any],
        request_id: Optional[str] = None,
    ) -> None:
        try:
            classification = write_time_result.get("classification", {})
            decision = write_time_result.get("decision", {})
            actions = [a.value for a in decision.get("actions", [])]

            reason_codes = self._determine_reason_codes(
                message_content, message_role, classification, decision
            )

            obs_reasons = []
            for rc in reason_codes:
                try:
                    obs_reasons.append(ObsDecisionReason(rc))
                except ValueError:
                    pass

            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    decision_logger.log_decision(
                        message_id=message_id,
                        conversation_id=conversation_id or "unknown",
                        user_id=user_id,
                        classified_type=classification.get("type", "unknown"),
                        embedded="embed" in actions,
                        summarized="summarize" in actions,
                        cached="cache" in actions,
                        discarded="discard" in actions,
                        reason_codes=obs_reasons,
                        confidence=classification.get("confidence", 0.0),
                        decision_metadata={
                            "write_time_result": write_time_result,
                            "message_role": message_role,
                        },
                        processing_time_ms=0.0,
                        request_id=request_id,
                    )
                )
            except RuntimeError:
                logger.debug(
                    "log_write_time_decision_no_running_loop",
                    message_id=message_id,
                )

            logger.info(
                "Write-time decision logged",
                message_id=message_id,
                classified_type=classification.get("type", "unknown"),
                reason_codes=reason_codes,
            )

            decision_payload = {
                "message_id": message_id,
                "conversation_id": conversation_id or "unknown",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "classified_type": classification.get("type", "unknown"),
                "classification": {
                    "type": classification.get("type", "unknown"),
                    "confidence": classification.get("confidence", 0.0),
                    "reason_codes": reason_codes,
                },
                "decisions": {
                    "embedded": "embed" in actions,
                    "summarized": "summarize" in actions,
                    "cached": "cache" in actions,
                    "discarded": "discard" in actions,
                },
                "message_content": message_content,
                "message_role": message_role,
                "confidence": classification.get("confidence", 0.0),
                "reason_codes": reason_codes,
                "request_id": request_id,
            }
            self._owner.write_decisions.append(decision_payload)
        except Exception as e:
            logger.error("Failed to log write-time decision", error=str(e))
