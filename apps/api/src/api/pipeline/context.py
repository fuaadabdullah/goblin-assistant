from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PipelineContext:
    """Typed carrier for all signals accumulated across the 4 pre-provider pipeline stages.

    Stages populate fields in order:
      1. Intent  → intent, task_type, complexity_score
      2. Memory  → assembled_context, context_metadata
      3. Routing → selected_provider, selected_model, fallback_chain
      4. Tools   → tool_candidates, tool_schemas
    """

    # Identity — always set at construction
    user_id: str
    conversation_id: str
    raw_message: str
    sanitized_message: str = ""

    # Stage 1: Intent
    intent: Optional[Any] = None  # IntentResult (Any avoids circular import at definition)
    task_type: Optional[str] = None
    complexity_score: float = 0.0

    # Stage 2: Memory / context assembly
    assembled_context: str = ""
    context_metadata: Dict[str, Any] = field(default_factory=dict)

    # Stage 3: Routing
    selected_provider: Optional[str] = None
    selected_model: Optional[str] = None
    provider_selection_reason: str = ""
    fallback_chain: List[str] = field(default_factory=list)

    # Stage 4: Tool selection
    tool_candidates: List[str] = field(default_factory=list)  # ordered tool names
    tool_schemas: List[Dict[str, Any]] = field(default_factory=list)  # OpenAI-format dicts

    # Final messages list — built by the caller after context assembly
    messages: List[Dict[str, Any]] = field(default_factory=list)

    # Pipeline health
    pipeline_error: Optional[str] = None
    used_fallback: bool = False
