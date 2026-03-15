"""
Earnings summarizer skill.

Fetches earnings data for a ticker and produces a structured summary
with beat/miss verdicts, key metrics, and recent-quarter trends.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..registry import ToolDefinition, ToolParameter, register_tool
from ...services.financial_data_service import financial_data_service
from ...services.financial_guardrails import safe_skill


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

@safe_skill
async def _handle_earnings_summarizer(
    ticker: str,
    num_quarters: int = 4,
) -> Dict[str, Any]:
    """Summarize recent earnings for *ticker*."""

    earnings = await financial_data_service.get_earnings(ticker)
    quote = await financial_data_service.get_current_quote(ticker)
    ratios = await financial_data_service.get_key_ratios(ticker)

    # Process quarterly earnings dates into a structured view
    raw_quarters: List[Dict[str, Any]] = earnings.get("earnings_dates", [])
    quarters: List[Dict[str, Any]] = []

    for q in raw_quarters[:num_quarters]:
        eps_est = q.get("eps_estimate")
        eps_act = q.get("eps_actual")
        surprise = q.get("surprise_percent")

        verdict = "N/A"
        if eps_est is not None and eps_act is not None:
            if eps_act > eps_est:
                verdict = "beat"
            elif eps_act < eps_est:
                verdict = "miss"
            else:
                verdict = "inline"

        quarters.append({
            "date": q.get("date"),
            "eps_estimate": eps_est,
            "eps_actual": eps_act,
            "surprise_pct": surprise,
            "verdict": verdict,
        })

    # Streak analysis
    beats = sum(1 for q in quarters if q["verdict"] == "beat")
    misses = sum(1 for q in quarters if q["verdict"] == "miss")
    streak_type = None
    streak_count = 0
    for q in quarters:
        if streak_type is None:
            streak_type = q["verdict"]
            streak_count = 1
        elif q["verdict"] == streak_type:
            streak_count += 1
        else:
            break

    # Latest quarter highlight
    latest = quarters[0] if quarters else None

    return {
        "ticker": ticker,
        "company_name": quote.get("name", ticker),
        "current_price": quote.get("price"),
        "latest_quarter": latest,
        "quarters": quarters,
        "summary": {
            "beats": beats,
            "misses": misses,
            "total": len(quarters),
            "current_streak": {
                "type": streak_type,
                "count": streak_count,
            } if streak_type and streak_type in ("beat", "miss") else None,
        },
        "key_metrics": {
            "trailing_eps": earnings.get("trailing_eps"),
            "forward_eps": earnings.get("forward_eps"),
            "pe_trailing": ratios.get("pe_trailing"),
            "pe_forward": ratios.get("pe_forward"),
            "peg_ratio": earnings.get("peg_ratio"),
            "earnings_growth_quarterly": earnings.get("earnings_quarterly_growth"),
            "revenue_growth": earnings.get("revenue_growth"),
        },
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register_tool(ToolDefinition(
    name="earnings_summarizer",
    description=(
        "Summarize recent earnings for a stock: beat/miss verdicts for each "
        "quarter, EPS actual vs. estimate, surprise percentage, streak "
        "analysis, and key valuation metrics."
    ),
    parameters=[
        ToolParameter(
            name="ticker",
            type="string",
            description="Stock ticker symbol, e.g. NVDA, AAPL",
        ),
        ToolParameter(
            name="num_quarters",
            type="integer",
            description="Number of recent quarters to include (1-8, default 4).",
            required=False,
            default=4,
        ),
    ],
    handler=_handle_earnings_summarizer,
    category="finance",
))
