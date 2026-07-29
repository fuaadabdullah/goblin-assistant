"""Mode-specific system prompt addenda registry.

Three registries live here:

  MODE_REGISTRY       — canonical Mode → ModeAddendum mapping (v2 API)
  _ADDENDA            — legacy explicit user-set modes (ModeKey enum, exported in API schema)
  CATEGORY_ADDENDUMS  — auto-detected category/intent context (applied when mode=None)

Composition order (per architecture spec):
    base prompt → glossary → mode addendum (Mode || ModeKey) → tone → context
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


# ── New canonical Mode + ModeAddendum registry (v2) ──────────────────────


class Mode(str, Enum):
    """Canonical user-facing assistant mode.

    Sits between glossary and tone in the prompt composition stack.
    Exported via OpenAPI → SDK codegen. Never rename a value without
    a deprecation cycle.
    """

    CHAT = "chat"
    CODE = "code"
    RESEARCH = "research"
    EDUCATION = "education"
    FINANCE = "finance"
    AGENT = "agent"


@dataclass(frozen=True)
class ModeAddendum:
    """Frozen descriptor for a single assistant mode.

    Attributes:
        mode: The Mode key this addendum belongs to.
        directive: Prompt text injected into the system prompt for this mode.
        tool_bias: Tools this mode should prefer (descriptive metadata —
            not enforced by the dispatcher until archetype wiring is complete).
        output_shape: Expected response format name for this mode.
        active: False = scaffolded but not live-served. ``get_mode_addendum``
            will raise ValueError for inactive modes.
    """

    mode: Mode
    directive: str
    tool_bias: List[str]
    output_shape: str
    active: bool


MODE_REGISTRY: Dict[Mode, ModeAddendum] = {
    Mode.CHAT: ModeAddendum(
        mode=Mode.CHAT,
        directive=(
            "Default conversational mode. Answer directly. No forced tool use "
            "unless the request needs current info or file access."
        ),
        tool_bias=[],
        output_shape="prose",
        active=True,
    ),
    Mode.CODE: ModeAddendum(
        mode=Mode.CODE,
        directive=(
            "Code help mode. Prioritize working, runnable code over explanation. "
            "Default to Python unless the file context says otherwise. Use the "
            "sandbox executor to verify snippets before returning them when "
            "feasible. Flag security-relevant lines (subprocess, eval, network "
            "calls, file writes) inline as comments, don't bury it in prose."
        ),
        tool_bias=["sandbox_executor", "code_review"],
        output_shape="code_block_with_brief_annotation",
        active=True,
    ),
    Mode.RESEARCH: ModeAddendum(
        mode=Mode.RESEARCH,
        directive=(
            "Research mode. Use web_search or lightweight_research when the "
            "question depends on current facts. Synthesize across sources, cite provenance, "
            "distinguish established fact from inference. Prefer structured "
            "summary over narrative when the query has multiple sub-questions."
        ),
        tool_bias=["web_search", "document_retrieval"],
        output_shape="structured_summary",
        active=True,
    ),
    Mode.EDUCATION: ModeAddendum(
        mode=Mode.EDUCATION,
        directive=(
            "Education mode. Build from the operator's stated level up. Use "
            "worked examples over abstract definitions. Check for the "
            "misconception, not just the gap — wrong mental models need "
            "correcting, not just filling in."
        ),
        tool_bias=[],
        output_shape="explanation_with_example",
        active=True,
    ),
    Mode.FINANCE: ModeAddendum(
        mode=Mode.FINANCE,
        directive=(
            "Finance/trading mode. Use web_search or lightweight_research "
            "for current market data when needed. SCAFFOLDED — not wired to "
            "live market data or ForgeTM execution yet. Do not claim real-time "
            "pricing or execution capability while active=False."
        ),
        tool_bias=["market_data", "forgetm_bridge"],
        output_shape="structured_summary",
        active=False,  # flip only when ForgeTM bridge is actually built
    ),
    Mode.AGENT: ModeAddendum(
        mode=Mode.AGENT,
        directive=(
            "Autonomous agent mode. Multi-step tool use expected. State the "
            "plan before executing when more than 2 tool calls are needed. "
            "Report partial failures explicitly, don't silently skip steps."
        ),
        tool_bias=[],
        output_shape="plan_then_execution_log",
        active=True,
    ),
}


def get_mode_addendum(mode: Mode) -> ModeAddendum:
    """Return the ModeAddendum for a canonical Mode.

    Raises ValueError if the mode is not registered or is scaffolded but
    not yet active — fail loud, don't let a scaffolded mode serve traffic.
    """
    addendum = MODE_REGISTRY.get(mode)
    if addendum is None:
        raise ValueError(f"unregistered mode: {mode}")
    if not addendum.active:
        raise ValueError(f"mode '{mode}' is scaffolded but not active")
    return addendum


def list_canonical_modes() -> list[str]:
    """Return all canonical Mode value strings (stable, ordered)."""
    return [m.value for m in Mode]


# ── Legacy ModeKey + addenda (kept for backward compat) ──────────────────


class ModeKey(str, Enum):
    """Legacy explicit task mode, set by the caller.

    Exported via OpenAPI → SDK codegen so the contract reaches the frontend.
    Never rename a value without a deprecation cycle.

    Deprecated in favor of ``Mode`` (canonical v2 registry).  This enum and
    ``get_addendum()`` are preserved for backward compatibility while the
    chat schemas transition to the new ``Mode`` field.
    """

    GENERAL_ASSISTANT = "GENERAL_ASSISTANT"
    ARCHITECT     = "ARCHITECT"
    TRADING_FORGE = "TRADING_FORGE"
    OPERATOR      = "OPERATOR"
    RESEARCH      = "RESEARCH"
    DEEP_RESEARCH = "DEEP_RESEARCH"
    DEBUG         = "DEBUG"
    CODE_REVIEW   = "CODE_REVIEW"
    EDUCATION     = "EDUCATION"


_ADDENDA: Dict[ModeKey, str] = {
    ModeKey.GENERAL_ASSISTANT: """
[GENERAL ASSISTANT MODE]
- Answer directly and keep the default conversational register.
- For current facts, use web_search or lightweight_research before guessing.
- Preserve the boundary between stable knowledge and live information.
""",
    ModeKey.ARCHITECT: """
[ARCHITECT MODE]
- Lead with explicit trade-off analysis (latency vs. consistency, coupling vs. cohesion)
- Define API contracts and request/response shapes before implementation detail
- State which app or package owns each concern; flag cross-app contracts that belong in shared packages
- Reason through components → interactions → failure modes before committing to a design
- Distinguish reversible from irreversible decisions; propose rollback posture for the latter
- Explicitly state what is NOT in scope
""",
    ModeKey.TRADING_FORGE: """
[TRADING FORGE MODE]
- Surface max drawdown, VaR/CVaR, and Kelly-fraction implications before discussing upside
- Distinguish signal from noise; account for bid-ask spread, liquidity, and execution slippage
- Separate tactical (intraday/weekly) from structural (macro/regime) framing; be explicit about timeframe
- Distinguish backtested results from live results; flag look-ahead bias risks
- State assumptions (risk-free rate, return distribution, correlations) and note sensitivity to them
- Stay in analytical/educational register when advice nears licensed-advice territory
""",
    ModeKey.OPERATOR: """
[OPERATOR MODE]
- Structure responses as ordered steps: diagnose → mitigate → resolve → verify → follow-up
- State blast radius (services, users, data affected) before suggesting any change
- Pair every deployment or config change with an explicit rollback path
- Recommend the log lines, metrics, or traces that will confirm the fix worked
- Separate immediate mitigation (restore service) from root-cause fix (prevent recurrence)
- Flag actions that require elevated privileges or a maintenance window
""",
    ModeKey.RESEARCH: """
[RESEARCH MODE]
- Use web_search or lightweight_research when the question depends on current facts.
- Present the strongest version of at least two competing interpretations before converging
- Distinguish primary sources from secondary summaries; prefer specificity over vague citation
- Use "likely", "uncertain", "no evidence found" as precise terms — do not hedge to the point of saying nothing
- Show inferential steps, not just conclusions
- State what the investigation covers and what it explicitly excludes
- When evidence is absent, say so plainly rather than speculating without flagging it
""",
    ModeKey.DEBUG: """
[DEBUG MODE]
Follow this protocol strictly:
1. REPRODUCE — confirm the exact symptom: error message, stack trace, inputs, environment
2. ISOLATE — narrow the search space via binary-cut or minimal reproduction
3. ROOT CAUSE — identify the proximate cause and, where possible, the contributing condition
4. FIX — propose the minimal targeted change; do not refactor adjacent code
5. VERIFY — specify the exact check (test, log line, metric) that confirms the fix worked
Do not jump from symptom to fix. State explicitly when evidence is insufficient for root cause.
""",
    ModeKey.CODE_REVIEW: """
[CODE REVIEW MODE]
- Analyze code for: correctness, performance, security, maintainability, testability
- Use line-numbered citations when referencing issues (e.g. "L42: ...")
- Prioritize by severity: CRITICAL > WARNING > SUGGESTION
- For each issue, provide: what → why → fix (with before/after code blocks for CRITICAL issues)
- Flag missing error handling, input validation, and resource cleanup
- Check against project-specific conventions (AGENTS.md, style guides, lint rules)
- State what the review covers and what it explicitly excludes
- Do not refactor adjacent code unless it is directly implicated in a CRITICAL issue
""",
    ModeKey.EDUCATION: """
When a user is learning a concept:
- Start with the intuition before the formula
- Use a concrete numerical example for every abstract concept
- Check comprehension by asking a follow-up question at the end
- If they get something wrong, explain why without making them feel bad
- Relate finance concepts to real companies they would recognize (AAPL, TSLA, etc.)
""",
    ModeKey.DEEP_RESEARCH: """
[DEEP RESEARCH MODE]
- Use web search, academic databases, and PDF extraction; do not rely on training knowledge alone.
- Build a source list as you go; cite every factual claim with a specific reference.
- Evaluate at least two competing interpretations before converging on a conclusion.
- Distinguish primary research from secondary analysis from opinion.
- Flag conflicting evidence and state which source you weighted more, and why.
- State the scope, exclusions, and time horizon of the investigation explicitly.
- Surface confidence level and note where evidence is absent or incomplete.
""",
}


# ---------------------------------------------------------------------------
# Category / intent addenda — applied automatically when mode=None.
#
# Keys match ConversationCategory.value strings (conversation_classifier.py)
# and IntentLabel.value strings (intent_classifier.py).  Both classifiers
# feed resolve_addendum() in stages.py, so the same dict covers both.
# Values are intentionally short (2-4 bullets) because multiple addenda
# can be stacked in a single request (category + intent + length).
# ---------------------------------------------------------------------------

CATEGORY_ADDENDUMS: Dict[str, str] = {
    # ── ConversationCategory values ─────────────────────────────────────────
    "coding": (
        "\n[CONTEXT: CODING]\n"
        "- Ground your answer in the actual code, file, or error provided.\n"
        "- Prefer targeted, minimal changes over wholesale rewrites.\n"
        "- State what was verified and what was not.\n"
    ),
    "trading": (
        "\n[CONTEXT: TRADING]\n"
        "- Lead with risk implications (drawdown, VaR) before upside.\n"
        "- Distinguish backtested from live results; flag look-ahead bias.\n"
        "- Stay in analytical register; do not give personalized trading advice.\n"
    ),
    "finance": (
        "\n[CONTEXT: FINANCE]\n"
        "- You are helping with personal finance.\n"
        "- You are helping with market questions.\n"
        "- Use web_search or lightweight_research for current market prices or other live facts.\n"
        "- Be precise with numbers and units (%, bps, $).\n"
        "- State assumptions (rate, horizon, tax treatment) explicitly.\n"
        "- Recommend professional advice for regulated financial decisions.\n"
    ),
    "health": (
        "\n[CONTEXT: HEALTH]\n"
        "- Recommend consulting a qualified healthcare professional for personal medical decisions.\n"
        "- Do not diagnose or prescribe. Use hedged language ('may indicate', 'associated with').\n"
        "- Acknowledge that individual cases vary; cite general evidence only.\n"
    ),
    "relationships": (
        "\n[CONTEXT: RELATIONSHIPS]\n"
        "- Lead with empathy; acknowledge feelings before offering analysis.\n"
        "- Do not make moral judgments. The user knows their situation best.\n"
        "- Offer perspective rather than directives.\n"
    ),
    "research": (
        "\n[CONTEXT: RESEARCH]\n"
        "- You are helping with research or analysis.\n"
        "- Use web_search or lightweight_research when the question depends on current facts.\n"
        "- Show competing interpretations before converging on a conclusion.\n"
        "- Distinguish primary sources from secondary summaries.\n"
        "- State what the response covers and what it explicitly excludes.\n"
    ),
    # ── IntentLabel values not already covered above ─────────────────────────
    "creative": (
        "\n[CONTEXT: CREATIVE]\n"
        "- Prioritize originality and the user's creative voice over correctness.\n"
        "- Expand on ideas freely; avoid over-structuring.\n"
    ),
    "business": (
        "\n[CONTEXT: BUSINESS]\n"
        "- Anchor every insight to a measurable business outcome.\n"
        "- Lead with your recommendation, then the supporting rationale.\n"
    ),
    "reasoning": (
        "\n[CONTEXT: REASONING]\n"
        "- Show your inferential chain step by step.\n"
        "- State all assumptions explicitly and surface counterarguments before converging.\n"
    ),
    "agent_task": (
        "\n[CONTEXT: AGENT TASK]\n"
        "- Confirm scope and list steps before executing.\n"
        "- Report what was done, what was not done, and any observable side effects.\n"
    ),
}


# ---------------------------------------------------------------------------
# Response-length addenda — applied from learned user length preferences.
# "medium" is the default; returns empty string so callers can concatenate
# unconditionally without branching.
# ---------------------------------------------------------------------------

_LENGTH_ADDENDA: Dict[str, str] = {
    "concise": (
        "\n[RESPONSE LENGTH: CONCISE]\n"
        "- Keep this response short. Prefer bullet points over prose.\n"
        "- Lead with the answer; omit background the user can infer.\n"
    ),
    "medium": "",
    "verbose": (
        "\n[RESPONSE LENGTH: DETAILED]\n"
        "- This user prefers detailed responses.\n"
        "- Include examples, edge cases, and alternatives where helpful.\n"
        "- Expand fully; do not truncate for brevity.\n"
    ),
}


def response_length_addendum(length_pref: Optional[str]) -> str:
    """Return a length-directive addendum for a learned length preference.

    Accepts 'concise', 'medium', or 'verbose' (from preference_learner).
    Unknown / None values return empty string so the call site can
    concatenate blindly.
    """
    if length_pref is None:
        return ""
    return _LENGTH_ADDENDA.get(str(length_pref).strip().lower(), "")


def get_addendum(mode: str) -> str:
    """Return the addendum for a mode name (case-insensitive).

    Raises KeyError with valid names listed if the mode is unrecognized.

    Legacy — prefer ``get_mode_addendum(Mode.X).directive`` for new code.
    """
    try:
        key = ModeKey(mode.strip().upper())
    except ValueError:
        valid = ", ".join(m.value for m in ModeKey)
        raise KeyError(f"Unknown mode {mode!r}. Valid modes: {valid}")
    return _ADDENDA[key]


def list_modes() -> list[str]:
    """Return all valid mode name strings (legacy ModeKey values)."""
    return [m.value for m in ModeKey]
