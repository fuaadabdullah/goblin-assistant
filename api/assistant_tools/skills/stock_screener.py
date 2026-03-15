"""
Stock screener skill.

Screens a universe of tickers against user-provided financial criteria
and returns matching stocks ranked by market cap.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..registry import ToolDefinition, ToolParameter, register_tool
from ...services.financial_data_service import financial_data_service
from ...services.financial_guardrails import safe_skill

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Default universe (S&P-500-like blue chips for fast screening)
# ---------------------------------------------------------------------------

_DEFAULT_UNIVERSE = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "BRK.B",
    "UNH", "JNJ", "V", "XOM", "JPM", "WMT", "MA", "PG", "HD", "CVX",
    "MRK", "ABBV", "LLY", "COST", "PEP", "KO", "AVGO", "TMO", "MCD",
    "CSCO", "ACN", "ABT", "DHR", "NKE", "TXN", "NEE", "PM", "UPS",
    "MS", "RTX", "HON", "LOW", "ORCL", "INTC", "AMD", "QCOM", "CRM",
    "IBM", "GE", "CAT", "BA", "DIS",
]


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

@safe_skill
async def _handle_stock_screener(
    min_market_cap: Optional[float] = None,
    max_market_cap: Optional[float] = None,
    max_pe: Optional[float] = None,
    min_pe: Optional[float] = None,
    min_dividend_yield: Optional[float] = None,
    max_debt_to_equity: Optional[float] = None,
    min_roe: Optional[float] = None,
    min_revenue_growth: Optional[float] = None,
    sector: Optional[str] = None,
    tickers: Optional[List[str]] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Screen stocks against financial criteria."""

    universe = tickers if tickers else _DEFAULT_UNIVERSE
    limit = max(1, min(limit, 50))

    results: List[Dict[str, Any]] = []
    errors: List[str] = []

    for ticker in universe:
        try:
            quote = await financial_data_service.get_current_quote(ticker)
            ratios = await financial_data_service.get_key_ratios(ticker)
        except Exception as exc:
            errors.append(f"{ticker}: {exc}")
            continue

        # Apply filters
        mcap = quote.get("market_cap")
        if min_market_cap is not None and (mcap is None or mcap < min_market_cap):
            continue
        if max_market_cap is not None and (mcap is None or mcap > max_market_cap):
            continue

        pe = ratios.get("pe_trailing")
        if max_pe is not None and (pe is None or pe > max_pe):
            continue
        if min_pe is not None and (pe is None or pe < min_pe):
            continue

        div_yield = ratios.get("dividend_yield")
        if min_dividend_yield is not None and (div_yield is None or div_yield < min_dividend_yield):
            continue

        dte = ratios.get("debt_to_equity")
        if max_debt_to_equity is not None and (dte is None or dte > max_debt_to_equity):
            continue

        roe = ratios.get("roe")
        if min_roe is not None and (roe is None or roe < min_roe):
            continue

        rev_growth = ratios.get("revenue_growth")
        if min_revenue_growth is not None and (rev_growth is None or rev_growth < min_revenue_growth):
            continue

        results.append({
            "ticker": ticker,
            "name": quote.get("name", ticker),
            "price": quote.get("price"),
            "market_cap": mcap,
            "pe_trailing": pe,
            "dividend_yield_pct": round(div_yield * 100, 2) if div_yield else None,
            "debt_to_equity": dte,
            "roe_pct": round(roe * 100, 2) if roe else None,
            "revenue_growth_pct": round(rev_growth * 100, 2) if rev_growth else None,
        })

    # Sort by market cap descending
    results.sort(key=lambda r: r.get("market_cap") or 0, reverse=True)
    results = results[:limit]

    return {
        "matches": len(results),
        "screened": len(universe),
        "criteria": {
            k: v
            for k, v in {
                "min_market_cap": min_market_cap,
                "max_market_cap": max_market_cap,
                "max_pe": max_pe,
                "min_pe": min_pe,
                "min_dividend_yield": min_dividend_yield,
                "max_debt_to_equity": max_debt_to_equity,
                "min_roe": min_roe,
                "min_revenue_growth": min_revenue_growth,
                "sector": sector,
            }.items()
            if v is not None
        },
        "results": results,
        "errors": errors if errors else None,
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register_tool(ToolDefinition(
    name="stock_screener",
    description=(
        "Screen stocks against financial criteria: market cap, P/E ratio, "
        "dividend yield, debt/equity, ROE, and revenue growth. "
        "Returns a ranked list of matching stocks with key metrics."
    ),
    parameters=[
        ToolParameter(
            name="min_market_cap",
            type="number",
            description="Minimum market cap in USD (e.g. 1e10 for $10B).",
            required=False,
        ),
        ToolParameter(
            name="max_market_cap",
            type="number",
            description="Maximum market cap in USD.",
            required=False,
        ),
        ToolParameter(
            name="max_pe",
            type="number",
            description="Maximum trailing P/E ratio (e.g. 25).",
            required=False,
        ),
        ToolParameter(
            name="min_pe",
            type="number",
            description="Minimum trailing P/E ratio.",
            required=False,
        ),
        ToolParameter(
            name="min_dividend_yield",
            type="number",
            description="Minimum dividend yield as decimal (e.g. 0.02 for 2%).",
            required=False,
        ),
        ToolParameter(
            name="max_debt_to_equity",
            type="number",
            description="Maximum debt-to-equity ratio (e.g. 50 means 50%).",
            required=False,
        ),
        ToolParameter(
            name="min_roe",
            type="number",
            description="Minimum ROE as decimal (e.g. 0.15 for 15%).",
            required=False,
        ),
        ToolParameter(
            name="min_revenue_growth",
            type="number",
            description="Minimum revenue growth rate as decimal (e.g. 0.1 for 10%).",
            required=False,
        ),
        ToolParameter(
            name="sector",
            type="string",
            description="Filter by sector name (e.g. 'Technology', 'Healthcare').",
            required=False,
        ),
        ToolParameter(
            name="tickers",
            type="array",
            description="Custom list of tickers to screen. If omitted, screens a default universe of ~50 large-cap stocks.",
            required=False,
            items={"type": "string"},
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Maximum results to return (1-50, default 20).",
            required=False,
            default=20,
        ),
    ],
    handler=_handle_stock_screener,
    category="finance",
))
