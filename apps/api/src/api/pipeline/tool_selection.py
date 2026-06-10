"""Intent-aware tool selection model.

Pure Python — no ML framework, no GPU, no network.

Algorithm
---------
1. Look up category weights for the intent label (coding → terminal=0.90, …).
2. Walk TOOL_REGISTRY and assign each tool the weight of its category.
3. Blend with intent confidence:  score * (0.5 + 0.5 * confidence).
   At confidence=0 scores halve (fewer tools pass threshold).
   At confidence=1 full weights apply.
4. Filter to score >= threshold (default 0.50).
5. Return tool names sorted descending by score.

CHAT intent is intentionally absent from the weights table → returns [] (no
tools for plain conversation).
"""

from __future__ import annotations

from typing import Dict, List

from .context import PipelineContext

# ---------------------------------------------------------------------------
# Intent → tool category weights
# Keys must match IntentLabel.value strings from intent_classifier.py.
# Category strings must match ToolDefinition.category values in registry.py.
# ---------------------------------------------------------------------------

_INTENT_CATEGORY_WEIGHTS: Dict[str, Dict[str, float]] = {
    "coding": {
        "terminal": 0.90,  # execute_code, sandbox
        "files": 0.80,  # read/write/search/list/…
        "git": 0.75,
        "github": 0.65,
        "web": 0.45,
        "research": 0.30,
        "memory": 0.60,
        "projects": 0.40,
        "tasks": 0.20,
        "academic": 0.00,
        "finance": 0.00,
    },
    "research": {
        "web": 0.95,
        "academic": 0.85,
        "research": 0.80,
        "memory": 0.70,
        "files": 0.40,
        "git": 0.00,
        "github": 0.00,
        "terminal": 0.10,
        "projects": 0.10,
        "tasks": 0.10,
        "finance": 0.10,
    },
    "finance": {
        "finance": 0.95,
        "web": 0.65,
        "academic": 0.30,
        "memory": 0.60,
        "research": 0.25,
        "files": 0.20,
        "tasks": 0.10,
        "projects": 0.10,
        "terminal": 0.00,
        "git": 0.00,
        "github": 0.00,
    },
    "agent_task": {
        "terminal": 0.90,
        "tasks": 0.85,
        "web": 0.80,
        "files": 0.75,
        "github": 0.70,
        "git": 0.60,
        "memory": 0.60,
        "projects": 0.55,
        "research": 0.50,
        "finance": 0.30,
        "academic": 0.20,
    },
    "business": {
        "web": 0.75,
        "research": 0.65,
        "academic": 0.40,
        "memory": 0.60,
        "finance": 0.50,
        "files": 0.30,
        "tasks": 0.40,
        "projects": 0.35,
        "terminal": 0.00,
        "git": 0.00,
        "github": 0.00,
    },
    "creative": {
        "web": 0.50,
        "memory": 0.60,
        "research": 0.30,
        "files": 0.20,
        "terminal": 0.00,
        "git": 0.00,
        "github": 0.00,
        "academic": 0.00,
        "finance": 0.00,
        "tasks": 0.00,
        "projects": 0.00,
    },
    "reasoning": {
        "web": 0.55,
        "research": 0.50,
        "academic": 0.45,
        "memory": 0.60,
        "finance": 0.30,
        "files": 0.20,
        "terminal": 0.00,
        "git": 0.00,
        "github": 0.00,
        "tasks": 0.00,
        "projects": 0.00,
    },
    # "chat" intentionally absent → select() returns []
}

_DEFAULT_THRESHOLD: float = 0.50


class ToolSelectionModel:
    """Lightweight intent-to-tool scorer.

    No external dependencies at construction time — TOOL_REGISTRY is imported
    lazily on first select() call (avoids circular imports at module load).
    """

    def __init__(self, threshold: float = _DEFAULT_THRESHOLD) -> None:
        self.threshold = threshold

    def select(self, ctx: PipelineContext) -> List[str]:
        """Return an ordered list of tool names appropriate for this request."""
        if ctx.intent is None:
            return []

        label: str = ctx.intent.label.value  # e.g. "coding"
        confidence: float = ctx.intent.confidence

        category_weights = _INTENT_CATEGORY_WEIGHTS.get(label)
        if not category_weights:
            return []

        from api.assistant_tools.registry import TOOL_REGISTRY  # lazy — avoids boot-time cycle

        scored: List[tuple[float, str]] = []
        for name, defn in TOOL_REGISTRY.items():
            cat_score = category_weights.get(defn.category, 0.0)
            blended = cat_score * (0.5 + 0.5 * confidence)
            if blended >= self.threshold:
                scored.append((blended, name))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [name for _, name in scored]


tool_selection_model = ToolSelectionModel()
