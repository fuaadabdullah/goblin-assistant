"""Canonical system-prompt composer.

Owns the fixed composition order for chat responses:

    1. base prompt            (config/system_prompt.py)
    2. glossary               (config/glossary.py)
    3. mode addendum          (config/mode_addendums.py)
    4. tone addendum          (config/tone_addendums.py)
    5. dynamic memory / context  (returned separately by the assembly service)

Call sites should never build this string piecewise — the contract is
"single function, single order, single string". That keeps wiring changes
trivial and makes the per-step order auditable from one place.

A `learning_boost` flag adds the existing EDUCATION_SYSTEM_ADDENDUM to
mode when the message classifier labels the turn as LEARNING. It is
applied as part of the mode addendum slot so it does not perturb the
order. Pass `learning_boost=False` to suppress it.
"""

from __future__ import annotations

from typing import Mapping, Optional

from . import glossary as _glossary
from . import mode_addendums as _mode_addendums
from . import tone_addendums as _tone_addendums
from .mode_addendums import Mode, ModeAddendum, get_mode_addendum
from .system_prompt import (
    EDUCATION_SYSTEM_ADDENDUM,
    get_configured_system_prompt,
)


def compose_system_prompt(
    *,
    tone: Optional[str] = None,
    mode: Optional[str] = None,
    learning_boost: bool = False,
    request_glossary: Optional[Mapping[str, str]] = None,
    user_glossary: Optional[Mapping[str, str]] = None,
    include_global_glossary: bool = True,
    unknown_mode: str = "skip",
) -> str:
    """Build the system prompt in the canonical composition order.

    Args:
        tone: One of `ToneMode` values or a raw string. Unknown → no tone
            addendum (tone is optional).
        mode: One of `ModeKey` values (legacy). Unknown behaviour is controlled
            by `unknown_mode` — either "skip" (silently omit) or "raise".
        mode: One of `ModeKey` values. Unknown behaviour is controlled by
            `unknown_mode` — either "skip" (silently omit) or "raise".
        learning_boost: If True, append `EDUCATION_SYSTEM_ADDENDUM` to the
            mode addendum slot for LEARNING-classified messages.
        request_glossary: Per-request glossary override (frontend-supplied).
        user_glossary: Per-user stored glossary (caller-resolved).
        include_global_glossary: Whether to include the code-defined
            `GLOBAL_GLOSSARY` in the glossary addendum.

    Returns:
        A single concatenated string ready to be sent as the system
        message content. Always non-empty (falls back to the base prompt
        when no addenda resolve).
    """
    base = get_configured_system_prompt()

    glossary_block = _glossary.format_glossary_addendum(
        request_glossary=request_glossary,
        user_glossary=user_glossary,
        include_global=include_global_glossary,
    )

    mode_block = _resolve_mode_block(mode, learning_boost, unknown_mode)

    tone_block = _tone_addendums.get_tone_addendum(tone)

    parts = [base, glossary_block, mode_block, tone_block]
    # Filter out empty strings; keep the order stable.
    return "\n\n".join(p for p in parts if p)


def compose_system_prompt_v2(
    *,
    mode: Mode = Mode.CHAT,
    tone: str = "default",
    dynamic_context: str = "",
) -> str:
    """Build the system prompt using the new canonical Mode registry.

    Args:
        mode: One of ``Mode`` values (canonical v2).  Raises ValueError if
            the mode is scaffolded but not active.
        tone: Tone name forwarded to ``get_tone_addendum``.
        dynamic_context: Optional context block (RAG, memory, etc.)
            appended at the end of the prompt.

    Returns:
        A single concatenated string ready to be sent as the system
        message content.
    """
    base = get_configured_system_prompt()

    glossary_block = _glossary.format_glossary_addendum()

    mode_addendum: ModeAddendum = get_mode_addendum(mode)
    mode_block = mode_addendum.directive

    tone_block = _tone_addendums.get_tone_addendum(tone)

    parts = [base, glossary_block, mode_block, tone_block, dynamic_context]
    return "\n\n".join(p for p in parts if p)


def _resolve_mode_block(mode: Optional[str], learning_boost: bool, unknown_mode: str) -> str:
    if mode:
        try:
            block = _mode_addendums.get_addendum(mode)
        except KeyError:
            if unknown_mode == "raise":
                raise
            block = ""
    else:
        block = ""

    if learning_boost and EDUCATION_SYSTEM_ADDENDUM:
        # Concatenate without losing the mode block content.
        block = (
            f"{block}\n\n{EDUCATION_SYSTEM_ADDENDUM}".strip()
            if block
            else EDUCATION_SYSTEM_ADDENDUM
        )

    return block
