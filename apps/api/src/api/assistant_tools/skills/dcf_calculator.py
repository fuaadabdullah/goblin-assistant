"""
DCF (Discounted Cash Flow) calculator skill.

Takes a ticker symbol and valuation assumptions, fetches real financial data,
projects free-cash-flow, discounts it, then returns an intrinsic value
estimate with a sensitivity matrix.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..registry import ToolDefinition, ToolParameter, register_tool
from ...services.financial_data_service import financial_data_service
from ...services.financial_guardrails import safe_skill


# ---------------------------------------------------------------------------
# Core calculation helpers
# ---------------------------------------------------------------------------

def _project_fcf(
    base_fcf: float,
    growth_rate: float,
    projection_years: int,
) -> List[Dict[str, Any]]:
    """Project FCF forward using a constant growth rate."""
    projections = []
    fcf = base_fcf
    for year in range(1, projection_years + 1):
        fcf *= 1 + growth_rate
        projections.append({
            "year": year,
            "projected_fcf": round(fcf, 2),
            "growth_rate": round(growth_rate * 100, 2),
        })
    return projections


def _discount_fcf(projections: List[Dict[str, Any]], wacc: float) -> float:
    """Return the present value of projected FCFs."""
    pv = 0.0
    for p in projections:
        pv += p["projected_fcf"] / (1 + wacc) ** p["year"]
    return pv


def _terminal_value(
    last_fcf: float,
    terminal_growth: float,
    wacc: float,
) -> float:
    """Gordon Growth Model terminal value."""
    if wacc <= terminal_growth:
        return 0.0
    return last_fcf * (1 + terminal_growth) / (wacc - terminal_growth)


def _sensitivity_matrix(
    base_fcf: float,
    projection_years: int,
    growth_rate: float,
    wacc: float,
    terminal_growth: float,
    net_debt: float,
    shares: float,
) -> List[Dict[str, Any]]:
    """Build a WACC × growth-rate sensitivity matrix for per-share value."""
    wacc_range = [wacc + d for d in (-0.02, -0.01, 0, 0.01, 0.02)]
    growth_range = [growth_rate + d for d in (-0.02, -0.01, 0, 0.01, 0.02)]

    rows = []
    for w in wacc_range:
        if w <= 0:
            continue
        row: Dict[str, Any] = {"wacc_pct": round(w * 100, 1)}
        for g in growth_range:
            proj = _project_fcf(base_fcf, g, projection_years)
            pv = _discount_fcf(proj, w)
            if proj:
                tv = _terminal_value(proj[-1]["projected_fcf"], terminal_growth, w)
                pv_tv = tv / (1 + w) ** projection_years
            else:
                pv_tv = 0.0
            ev = pv + pv_tv
            equity = ev - net_debt
            per_share = round(equity / shares, 2) if shares else 0.0
            row[f"growth_{round(g * 100, 1)}"] = per_share
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

@safe_skill
async def _handle_dcf_calculator(
    ticker: str,
    wacc: Optional[float] = None,
    growth_rate: Optional[float] = None,
    projection_years: int = 5,
    terminal_growth: float = 0.025,
) -> Dict[str, Any]:
    """Run a DCF valuation for *ticker*."""

    # Fetch real data
    financials = await financial_data_service.get_financials(ticker)
    quote = await financial_data_service.get_current_quote(ticker)
    ratios = await financial_data_service.get_key_ratios(ticker)

    # Base free cash flow
    base_fcf = financials.get("free_cash_flow")
    if not base_fcf or base_fcf <= 0:
        return {
            "ticker": ticker,
            "error": (
                "Cannot run DCF: free cash flow is unavailable or negative "
                f"({base_fcf}). The company may not be FCF-positive."
            ),
        }

    # Shares outstanding
    shares = financials.get("shares_outstanding") or 1
    current_price = quote.get("price") or 0

    # Net debt = total_debt - total_cash
    total_debt = financials.get("total_debt") or 0
    total_cash = financials.get("total_cash") or 0
    net_debt = total_debt - total_cash

    # Default WACC: use beta-implied cost of equity blended with debt cost
    if wacc is None:
        beta = ratios.get("beta") or 1.0
        risk_free = 0.043  # ~10Y US Treasury approximation
        equity_risk_premium = 0.055
        cost_of_equity = risk_free + beta * equity_risk_premium
        # Simple blend: assume 70% equity / 30% debt at 5% pre-tax
        wacc = 0.7 * cost_of_equity + 0.3 * 0.05 * (1 - 0.21)
    wacc = max(wacc, 0.01)

    # Default growth: use revenue growth if available, else 5%
    if growth_rate is None:
        rev_growth = ratios.get("revenue_growth") if ratios.get("revenue_growth") else None
        # revenue_growth from yfinance might be a pct like 0.08 for 8%
        if rev_growth is not None and -0.5 < rev_growth < 1.0:
            growth_rate = rev_growth
        else:
            growth_rate = 0.05

    projection_years = max(1, min(projection_years, 20))

    # Project & discount
    projections = _project_fcf(base_fcf, growth_rate, projection_years)
    pv_fcf = _discount_fcf(projections, wacc)
    tv = _terminal_value(projections[-1]["projected_fcf"], terminal_growth, wacc)
    pv_tv = tv / (1 + wacc) ** projection_years

    enterprise_value = pv_fcf + pv_tv
    equity_value = enterprise_value - net_debt
    per_share_value = equity_value / shares if shares else 0.0
    upside = ((per_share_value / current_price) - 1) * 100 if current_price else None

    sensitivity = _sensitivity_matrix(
        base_fcf, projection_years, growth_rate, wacc,
        terminal_growth, net_debt, shares,
    )

    return {
        "ticker": ticker,
        "valuation": {
            "intrinsic_value_per_share": round(per_share_value, 2),
            "current_price": current_price,
            "upside_pct": round(upside, 1) if upside is not None else None,
            "enterprise_value": round(enterprise_value, 2),
            "equity_value": round(equity_value, 2),
        },
        "assumptions": {
            "wacc_pct": round(wacc * 100, 2),
            "growth_rate_pct": round(growth_rate * 100, 2),
            "terminal_growth_pct": round(terminal_growth * 100, 2),
            "projection_years": projection_years,
            "base_fcf": base_fcf,
            "net_debt": net_debt,
            "shares_outstanding": shares,
        },
        "projections": projections,
        "sensitivity_matrix": sensitivity,
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register_tool(ToolDefinition(
    name="dcf_calculator",
    description=(
        "Run a Discounted Cash Flow (DCF) valuation for a stock. "
        "Fetches real financial data, projects free cash flow, discounts it "
        "at WACC, and returns an intrinsic value estimate with a sensitivity "
        "table across WACC and growth-rate assumptions."
    ),
    parameters=[
        ToolParameter(
            name="ticker",
            type="string",
            description="Stock ticker symbol, e.g. AAPL, MSFT",
        ),
        ToolParameter(
            name="wacc",
            type="number",
            description="Weighted-average cost of capital as a decimal (e.g. 0.10 for 10%). If omitted, estimated from beta.",
            required=False,
        ),
        ToolParameter(
            name="growth_rate",
            type="number",
            description="Annual FCF growth rate as a decimal (e.g. 0.08 for 8%). If omitted, estimated from revenue growth.",
            required=False,
        ),
        ToolParameter(
            name="projection_years",
            type="integer",
            description="Number of years to project (1-20, default 5).",
            required=False,
            default=5,
        ),
        ToolParameter(
            name="terminal_growth",
            type="number",
            description="Perpetual growth rate for terminal value (default 0.025 = 2.5%).",
            required=False,
            default=0.025,
        ),
    ],
    handler=_handle_dcf_calculator,
    category="finance",
))
