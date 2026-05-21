"""
System + Guardrails layer assembler.

Fixed‑cost layer: the system prompt is always included and never trimmed
below its budget allocation.
"""

from typing import Optional

import structlog

from ...config.system_prompt import get_configured_system_prompt
from ...utils.tokenizer import count_tokens, trim_to_tokens
from .models import ContextBudget, ContextLayer

logger = structlog.get_logger()


async def assemble_system_layer(
    remaining_tokens: int,
    budget: ContextBudget,
) -> Optional[ContextLayer]:
    """Assemble System + Guardrails layer (Fixed Cost)."""
    if remaining_tokens < budget.system_tokens:
        return None

    system_prompt = get_configured_system_prompt()
    tokens = count_tokens(system_prompt)

    if tokens > budget.system_tokens:
        system_prompt = trim_to_tokens(system_prompt, budget.system_tokens)
        tokens = budget.system_tokens

    return ContextLayer(
        name="system",
        content=system_prompt,
        tokens=tokens,
        metadata={
            "type": "system",
            "fixed_cost": True,
            "description": "System prompt and guardrails",
        },
    )
