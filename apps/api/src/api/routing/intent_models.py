"""
Intent classification models — enums, dataclasses, and mapping helpers.

Extracted from intent_classifier.py for modularity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class IntentLabel(str, Enum):
    CODING = "coding"
    RESEARCH = "research"
    CREATIVE = "creative"
    BUSINESS = "business"
    FINANCE = "finance"
    REASONING = "reasoning"
    AGENT_TASK = "agent_task"


@dataclass
class IntentResult:
    label: IntentLabel
    confidence: float  # 0.0–1.0
    method: str  # "keyword" | "embedding"
    runner_up: Optional[IntentLabel] = None
    runner_up_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label.value,
            "confidence": round(self.confidence, 4),
            "method": self.method,
            "runner_up": self.runner_up.value if self.runner_up else None,
            "runner_up_confidence": round(self.runner_up_confidence, 4),
        }


def map_intent_to_task_type(intent: IntentResult) -> Optional[str]:
    """
    Map an IntentResult to a SmartRouter TaskType value string.
    Returns None for intents that don't map cleanly (router falls back to PromptClassifier).
    """
    _MAP = {
        IntentLabel.CODING: "code",  # TaskType.CODE_GENERATION
        IntentLabel.RESEARCH: "summary",  # TaskType.SUMMARIZATION
        IntentLabel.REASONING: "reasoning",  # TaskType.REASONING
        IntentLabel.FINANCE: "reasoning",  # finance is reasoning-heavy
        IntentLabel.CREATIVE: None,
        IntentLabel.BUSINESS: None,
        IntentLabel.AGENT_TASK: None,
    }
    return _MAP.get(intent.label)


__all__ = [
    "IntentLabel",
    "IntentResult",
    "map_intent_to_task_type",
]
