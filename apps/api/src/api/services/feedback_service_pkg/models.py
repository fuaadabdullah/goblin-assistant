from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class FeedbackSignal:
    """Canonical feedback signal names."""

    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    REGENERATE = "regenerate"
    DELETE = "delete"
    CONTINUE = "continue"
    PROVIDER_SWITCH = "provider_switch"
    MODEL_SWITCH = "model_switch"
    COPY = "copy"


@dataclass
class FeedbackContext:
    """Context captured at the time a feedback signal is emitted."""

    user_id: str
    conversation_id: str
    message_id: str
    request_id: Optional[str] = None
    department: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    task_type: Optional[str] = None
    intent_label: Optional[str] = None
    complexity_score: Optional[float] = None
    previous_provider: Optional[str] = None
    previous_model: Optional[str] = None


@dataclass
class FeedbackEvent:
    """A single feedback event ready for recording."""

    signal: str
    rating: Optional[int] = None
    context: Optional[FeedbackContext] = None
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeedbackStats:
    """Aggregated feedback statistics for dashboard."""

    total_events: int = 0
    thumbs_up_count: int = 0
    thumbs_down_count: int = 0
    regenerate_count: int = 0
    delete_count: int = 0
    continue_count: int = 0
    copy_count: int = 0
    provider_switch_count: int = 0
    model_switch_count: int = 0
    thumbs_up_rate: float = 0.0
    by_department: Dict[str, Dict[str, int]] = field(default_factory=dict)
    by_provider: Dict[str, Dict[str, int]] = field(default_factory=dict)
    recent_events: List[Dict[str, Any]] = field(default_factory=list)
