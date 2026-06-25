from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, NamedTuple, Optional


@dataclass(frozen=True)
class RequestContext:
    user_id: str
    conversation_id: str
    raw_message: str
    sanitized_message: str = ""


@dataclass(frozen=True)
class DecisionContext:
    """Output of stages 1 (intent) and 2 (memory)."""

    intent: Optional[Any] = None  # IntentResult — Any avoids circular import at definition
    task_type: Optional[str] = None
    complexity_score: float = 0.0
    assembled_context: str = ""
    context_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionContext:
    """Output of stage 3 (routing). Provider fields are internal — never expose to client."""

    selected_department: Optional[str] = None
    department_selection_reason: str = ""
    selected_provider: Optional[str] = None
    selected_model: Optional[str] = None
    fallback_chain: List[str] = field(default_factory=list)
    # Scored candidates from ProviderSelectionModel: {provider_id: pct}. Internal only.
    provider_scores: Dict[str, int] = field(default_factory=dict)
    # ID used to attribute routing outcomes back to this decision for weight updates.
    routing_id: Optional[str] = None


@dataclass(frozen=True)
class ResponseContext:
    """Output of stage 4 (tool selection)."""

    tool_candidates: List[str] = field(default_factory=list)
    tool_schemas: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class PipelineHealth:
    error: Optional[str] = None
    used_fallback: bool = False
    failed_stage: Optional[str] = None  # "intent" | "memory" | "routing" | "tools"


class PipelineResult(NamedTuple):
    request: RequestContext
    decision: DecisionContext
    execution: ExecutionContext
    response: ResponseContext
    health: PipelineHealth
