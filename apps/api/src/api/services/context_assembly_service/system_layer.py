"""
System + Guardrails layer assembler.

Fixed‑cost layer: the system prompt is always included and never trimmed
below its budget allocation.
"""

from datetime import datetime, timezone
from typing import Optional

import structlog

from ...config.system_prompt import get_configured_system_prompt
from ...core.tokenization import count_tokens, trim_to_tokens
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
