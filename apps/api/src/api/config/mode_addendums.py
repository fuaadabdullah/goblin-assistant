"""Mode-specific system prompt addenda registry."""

from enum import Enum
from typing import Dict


class ModeKey(str, Enum):
    ARCHITECT = "ARCHITECT"
    TRADING_FORGE = "TRADING_FORGE"
    OPERATOR = "OPERATOR"
    RESEARCH = "RESEARCH"
    DEBUG = "DEBUG"
    EDUCATION = "EDUCATION"


_ADDENDA: Dict[ModeKey, str] = {
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
    ModeKey.EDUCATION: """
When a user is learning a concept:
- Start with the intuition before the formula
- Use a concrete numerical example for every abstract concept
- Check comprehension by asking a follow-up question at the end
- If they get something wrong, explain why without making them feel bad
- Relate finance concepts to real companies they would recognize (AAPL, TSLA, etc.)
""",
}


def get_addendum(mode: str) -> str:
    """Return the addendum for a mode name (case-insensitive).

    Raises KeyError with valid names listed if the mode is unrecognized.
    """
    try:
        key = ModeKey(mode.strip().upper())
    except ValueError:
        valid = ", ".join(m.value for m in ModeKey)
        raise KeyError(f"Unknown mode {mode!r}. Valid modes: {valid}")
    return _ADDENDA[key]


def list_modes() -> list[str]:
    """Return all valid mode name strings."""
    return [m.value for m in ModeKey]
