"""
Portfolio analyzer skill.

Takes a list of holdings (ticker + shares/weight), fetches historical
prices, and returns allocation, risk metrics, correlation data, and
performance comparison against a benchmark.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from ..registry import ToolDefinition, ToolParameter, register_tool
from ...services.financial_data_service import financial_data_service
from ...services.financial_guardrails import safe_skill


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _daily_returns(prices: List[float]) -> List[float]:
    """Calculate simple daily returns from a price series."""
    if len(prices) < 2:
        return []
    return [(prices[i] / prices[i - 1]) - 1 for i in range(1, len(prices))]


def _annualized_return(daily_rets: List[float]) -> float:
    cumulative = 1.0
    for r in daily_rets:
        cumulative *= 1 + r
    if len(daily_rets) == 0:
        return 0.0
    return cumulative ** (252 / len(daily_rets)) - 1


def _annualized_volatility(daily_rets: List[float]) -> float:
    if len(daily_rets) < 2:
        return 0.0
    mean = sum(daily_rets) / len(daily_rets)
    var = sum((r - mean) ** 2 for r in daily_rets) / (len(daily_rets) - 1)
    return math.sqrt(var) * math.sqrt(252)


def _sharpe_ratio(ann_return: float, ann_vol: float, risk_free: float = 0.043) -> Optional[float]:
    if ann_vol == 0:
        return None
    return (ann_return - risk_free) / ann_vol


def _max_drawdown(prices: List[float]) -> float:
    if not prices:
        return 0.0
    peak = prices[0]
    max_dd = 0.0
    for p in prices:
        if p > peak:
            peak = p
        dd = (peak - p) / peak
        if dd > max_dd:
            max_dd = dd
    return max_dd


def _var_95(daily_rets: List[float]) -> float:
    """Historical Value at Risk at 95% confidence."""
    if len(daily_rets) < 20:
        return 0.0
    sorted_rets = sorted(daily_rets)
    idx = int(len(sorted_rets) * 0.05)
    return sorted_rets[idx]


def _correlation(a: List[float], b: List[float]) -> float:
    """Pearson correlation between two return series of equal length."""
    n = min(len(a), len(b))
    if n < 2:
        return 0.0
    a, b = a[:n], b[:n]
    ma = sum(a) / n
    mb = sum(b) / n
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / (n - 1)
    sa = math.sqrt(sum((x - ma) ** 2 for x in a) / (n - 1))
    sb = math.sqrt(sum((x - mb) ** 2 for x in b) / (n - 1))
    if sa == 0 or sb == 0:
        return 0.0
    return cov / (sa * sb)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

@safe_skill
async def _handle_portfolio_analyzer(
    holdings: List[Dict[str, Any]],
    benchmark: str = "SPY",
    period: str = "1y",
) -> Dict[str, Any]:
    """Analyze a portfolio of stock holdings."""

    if not holdings:
        return {"error": "No holdings provided."}

    # Normalise holdings: accept either {ticker, shares} or {ticker, weight}
    tickers = []
    raw_weights: Dict[str, float] = {}
    for h in holdings:
        t = h.get("ticker", "").strip().upper()
        if not t:
            continue
        tickers.append(t)
        if "weight" in h:
            raw_weights[t] = float(h["weight"])
        elif "shares" in h:
            raw_weights[t] = float(h["shares"])  # will normalise later
        else:
            raw_weights[t] = 1.0

    if not tickers:
        return {"error": "No valid tickers in holdings."}

    # Fetch price histories in parallel-ish (sequential but cached)
    histories: Dict[str, List[float]] = {}
    for t in tickers:
        hist = await financial_data_service.get_price_history(t, period=period, interval="1d")
        close_prices = [d["close"] for d in hist.get("data", [])]
        if close_prices:
            histories[t] = close_prices

    if not histories:
        return {"error": "Could not retrieve price data for any holdings."}

    # Filter to tickers we actually got data for
    tickers = [t for t in tickers if t in histories]

    # Normalise weights to sum to 1.0
    total_w = sum(raw_weights.get(t, 1.0) for t in tickers)
    weights = {t: raw_weights.get(t, 1.0) / total_w for t in tickers}

    # Per-holding metrics
    all_daily_rets: Dict[str, List[float]] = {}
    holding_metrics: List[Dict[str, Any]] = []
    for t in tickers:
        dr = _daily_returns(histories[t])
        all_daily_rets[t] = dr
        ann_ret = _annualized_return(dr)
        ann_vol = _annualized_volatility(dr)
        holding_metrics.append({
            "ticker": t,
            "weight_pct": round(weights[t] * 100, 2),
            "annualized_return_pct": round(ann_ret * 100, 2),
            "annualized_volatility_pct": round(ann_vol * 100, 2),
            "sharpe_ratio": round(_sharpe_ratio(ann_ret, ann_vol), 2) if _sharpe_ratio(ann_ret, ann_vol) is not None else None,
            "max_drawdown_pct": round(_max_drawdown(histories[t]) * 100, 2),
        })

    # Portfolio-level metrics (weighted daily returns)
    min_len = min(len(all_daily_rets[t]) for t in tickers)
    if min_len < 2:
        return {
            "error": "Insufficient price data for portfolio analysis.",
            "holdings": holding_metrics,
        }

    port_daily_rets = []
    for i in range(min_len):
        day_ret = sum(weights[t] * all_daily_rets[t][i] for t in tickers)
        port_daily_rets.append(day_ret)

    port_ann_ret = _annualized_return(port_daily_rets)
    port_ann_vol = _annualized_volatility(port_daily_rets)
    port_sharpe = _sharpe_ratio(port_ann_ret, port_ann_vol)

    # Reconstruct portfolio price for drawdown
    port_prices = [1.0]
    for r in port_daily_rets:
        port_prices.append(port_prices[-1] * (1 + r))
    port_max_dd = _max_drawdown(port_prices)
    port_var95 = _var_95(port_daily_rets)

    # Correlation matrix
    corr_matrix: Dict[str, Dict[str, float]] = {}
    for a in tickers:
        corr_matrix[a] = {}
        for b in tickers:
            corr_matrix[a][b] = round(
                _correlation(all_daily_rets[a][:min_len], all_daily_rets[b][:min_len]),
                3,
            )

    # Benchmark comparison
    bench_data: Optional[Dict[str, Any]] = None
    try:
        bench_hist = await financial_data_service.get_price_history(benchmark, period=period, interval="1d")
        bench_prices = [d["close"] for d in bench_hist.get("data", [])]
        if bench_prices:
            bench_dr = _daily_returns(bench_prices)
            bench_ann_ret = _annualized_return(bench_dr)
            bench_ann_vol = _annualized_volatility(bench_dr)
            bench_data = {
                "ticker": benchmark,
                "annualized_return_pct": round(bench_ann_ret * 100, 2),
                "annualized_volatility_pct": round(bench_ann_vol * 100, 2),
                "sharpe_ratio": round(_sharpe_ratio(bench_ann_ret, bench_ann_vol), 2) if _sharpe_ratio(bench_ann_ret, bench_ann_vol) is not None else None,
                "max_drawdown_pct": round(_max_drawdown(bench_prices) * 100, 2),
            }
    except Exception:
        pass

    return {
        "portfolio": {
            "annualized_return_pct": round(port_ann_ret * 100, 2),
            "annualized_volatility_pct": round(port_ann_vol * 100, 2),
            "sharpe_ratio": round(port_sharpe, 2) if port_sharpe is not None else None,
            "max_drawdown_pct": round(port_max_dd * 100, 2),
            "var_95_daily_pct": round(port_var95 * 100, 2),
        },
        "holdings": holding_metrics,
        "correlation_matrix": corr_matrix,
        "benchmark": bench_data,
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register_tool(ToolDefinition(
    name="portfolio_analyzer",
    description=(
        "Analyze a stock portfolio: calculate allocation weights, annualized "
        "return, volatility, Sharpe ratio, max drawdown, Value-at-Risk, "
        "and a correlation matrix. Compares performance to a benchmark (default SPY)."
    ),
    parameters=[
        ToolParameter(
            name="holdings",
            type="array",
            description=(
                'Array of holdings, each with "ticker" (string) and either '
                '"shares" (number) or "weight" (number). '
                'Example: [{"ticker":"AAPL","shares":10},{"ticker":"MSFT","shares":5}]'
            ),
            items={"type": "object"},
        ),
        ToolParameter(
            name="benchmark",
            type="string",
            description="Benchmark ticker for comparison (default SPY).",
            required=False,
            default="SPY",
        ),
        ToolParameter(
            name="period",
            type="string",
            description="Lookback period: 1mo, 3mo, 6mo, 1y, 2y, 5y (default 1y).",
            required=False,
            default="1y",
        ),
    ],
    handler=_handle_portfolio_analyzer,
    category="finance",
))
