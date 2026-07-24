"""Tone-specific system prompt addenda registry.

Composition order in chat endpoints (per architecture spec):
    1. base prompt        (config/system_prompt.py)
    2. glossary           (config/glossary.py)
    3. mode addendum      (config/mode_addendums.py)
    4. tone addendum      (this module)  ← wired here
    5. dynamic memory / context (context_assembly_service)

`ToneMode` is exposed on chat request schemas so the contract gate (OpenAPI
export → SDK codegen) carries the enum into the frontend types for free.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict


class ToneMode(str, Enum):
    """Voice / register the assistant should answer in.

    Values are intentionally broad and additive — never rename a value
    without a deprecation cycle because it is part of the public API
    contract (exported via OpenAPI and consumed by the SDK).
    """

    DEFAULT = "DEFAULT"
    FORMAL = "FORMAL"
    CASUAL = "CASUAL"
    TECHNICAL = "TECHNICAL"
    EDUCATIONAL = "EDUCATIONAL"
    EXECUTIVE = "EXECUTIVE"


_TONE_ADDENDA: Dict[ToneMode, str] = {
    ToneMode.DEFAULT: "",
    ToneMode.FORMAL: (
        "\n[TONE: FORMAL]\n"
        "- Use precise, professional language. No slang, no contractions.\n"
        "- Prefer full sentences; avoid rhetorical asides.\n"
        '- Cite uncertainty in measured terms (e.g. "appears to", "based on").\n'
    ),
    ToneMode.CASUAL: (
        "\n[TONE: CASUAL]\n"
        "- Be conversational and warm. Contractions are fine.\n"
        "- Keep it short by default; one or two short paragraphs max.\n"
        "- Plain language over jargon unless the user signals otherwise.\n"
    ),
    ToneMode.TECHNICAL: (
        "\n[TONE: TECHNICAL]\n"
        "- Write for an engineering audience. Use domain vocabulary without\n"
        "  glossing; skip introductory framing.\n"
        "- Show code, file paths, and command lines verbatim.\n"
        "- State assumptions and edge cases explicitly. Call out tradeoffs.\n"
    ),
    ToneMode.EDUCATIONAL: (
        "\n[TONE: EDUCATIONAL]\n"
        "- Lead with the intuition before the formal definition.\n"
        "- Use a concrete example for every abstract concept.\n"
        "- Check comprehension at the end with a short follow-up question.\n"
        "- If the user gets something wrong, correct without condescension.\n"
    ),
    ToneMode.EXECUTIVE: (
        "\n[TONE: EXECUTIVE]\n"
        "- Lead with the recommendation or decision in the first sentence.\n"
        "- Use bullet structure: decision, why, risks, ask.\n"
        "- Quantify impact when possible. Skip background the audience already has.\n"
    ),
}


def get_tone_addendum(tone: str | ToneMode | None) -> str:
    """Return the tone addendum for a tone name. Unknown/None → DEFAULT (empty).

    Accepts either a `ToneMode` member or a raw string. Case-insensitive on
    string input. Returns an empty string for the default tone and for any
    unrecognized value so the call site can blindly concatenate the result
    without conditional branching.
    """
    if tone is None:
        return ""
    if isinstance(tone, ToneMode):
        return _TONE_ADDENDA.get(tone, "")
    try:
        key = ToneMode(str(tone).strip().upper())
    except ValueError:
        return ""
    return _TONE_ADDENDA.get(key, "")


def list_tones() -> list[str]:
    """Return all valid tone name strings (stable, ordered)."""
    return [t.value for t in ToneMode]
