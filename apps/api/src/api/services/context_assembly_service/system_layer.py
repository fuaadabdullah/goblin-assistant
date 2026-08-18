"""
System + Guardrails layer assembler.

Fixed‑cost layer: the system prompt is always included and never trimmed
below its budget allocation.
"""

from datetime import datetime, timezone
from typing import Dict, Optional

import structlog

from ...config.system_prompt import get_configured_system_prompt
from ...core.tokenization import count_tokens, trim_to_tokens
from . import budget_manager as _bm
from .models import ContextBudget, ContextLayer

logger = structlog.get_logger()


def _runtime_context_block() -> str:
    """Build the runtime context prefix that stays in front of the system prompt."""
    current_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return f"Runtime context:\nCurrent UTC date/time: {current_utc}"


async def assemble_system_layer(
    remaining_tokens: int,
    budget: ContextBudget,
) -> Optional[ContextLayer]:
    """Assemble System + Guardrails layer (Fixed Cost)."""
    if remaining_tokens < budget.system_tokens:
        return None

    system_prompt = get_configured_system_prompt()
    runtime_context = _runtime_context_block()
    enriched_prompt = f"{runtime_context}\n\n{system_prompt}"
    tokens = count_tokens(enriched_prompt)

    if tokens > budget.system_tokens:
        enriched_prompt = trim_to_tokens(enriched_prompt, budget.system_tokens)
        tokens = budget.system_tokens

    return ContextLayer(
        name="system",
        content=enriched_prompt,
        tokens=tokens,
        metadata={
            "type": "system",
            "fixed_cost": True,
            "description": "System prompt and guardrails",
        },
    )


async def build_default_system_message() -> Optional[Dict[str, str]]:
    """Fixed-cost system+guardrails+date layer as a ready-to-send chat message.

    Convenience wrapper around assemble_system_layer() for call sites that
    skip full context assembly (streaming, guest/no-conversation endpoints)
    but must still send *something* grounding the model in its identity,
    guardrails, and the current date — instead of sending raw messages with
    no system role at all.
    """
    budget = _bm.load_budget_config()
    layer = await assemble_system_layer(budget.total_tokens, budget)
    if not layer:
        return None
    return {"role": "system", "content": layer.content}
