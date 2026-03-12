"""
Visualization extraction service.

Transforms tool execution results into chart-ready data structures
that the frontend can render with Recharts.

Each extractor maps a tool name to a list of VisualizationBlock dicts:
    {
        "type": "line_chart" | "bar_chart" | "pie_chart" | "table" | "heatmap",
        "title": str,
        "data": list | dict,
        "config": dict,          # axis labels, color keys, etc.
    }
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)

VisualizationBlock = Dict[str, Any]


# ---------------------------------------------------------------------------
# Per-tool extractors
# ---------------------------------------------------------------------------

def _extract_dcf_visualizations(
    args: Dict[str, Any],
    result: Dict[str, Any],
) -> List[VisualizationBlock]:
    """Extract visualizations from a DCF valuation result."""
    blocks: List[VisualizationBlock] = []
    ticker = result.get("ticker", args.get("ticker", ""))

    # 1. FCF projections → bar chart
    projections = result.get("projections", [])
    if projections:
        blocks.append({
            "type": "bar_chart",
            "title": f"{ticker} — Projected Free Cash Flow",
            "data": [
                {"year": f"Year {p['year']}", "fcf": p["projected_fcf"]}
                for p in projections
            ],
            "config": {
                "xKey": "year",
                "bars": [{"dataKey": "fcf", "label": "FCF ($)"}],
            },
        })

    # 2. Sensitivity matrix → table
    matrix = result.get("sensitivity_matrix", [])
    if matrix:
        # Extract growth rate columns from the first row's keys
        growth_keys = [k for k in matrix[0] if k.startswith("growth_")]
        columns = [
            {"key": "wacc_pct", "label": "WACC %"},
            *[
                {"key": k, "label": f"Growth {k.replace('growth_', '')}%"}
                for k in growth_keys
            ],
        ]
        blocks.append({
            "type": "table",
            "title": f"{ticker} — Sensitivity Analysis (Price per Share)",
            "data": matrix,
            "config": {
                "columns": columns,
                "highlight": {
                    "key": "wacc_pct",
                    "value": result.get("assumptions", {}).get("wacc_pct"),
                },
            },
        })

    # 3. Valuation summary → table
    valuation = result.get("valuation", {})
    assumptions = result.get("assumptions", {})
    if valuation:
        blocks.append({
            "type": "table",
            "title": f"{ticker} — DCF Valuation Summary",
            "data": [
                {"metric": "Intrinsic Value / Share", "value": f"${valuation.get('intrinsic_value_per_share', 0):,.2f}"},
                {"metric": "Current Price", "value": f"${valuation.get('current_price', 0):,.2f}"},
                {"metric": "Upside", "value": f"{valuation.get('upside_pct', 0):.1f}%" if valuation.get("upside_pct") is not None else "N/A"},
                {"metric": "WACC", "value": f"{assumptions.get('wacc_pct', 0):.1f}%"},
                {"metric": "Growth Rate", "value": f"{assumptions.get('growth_rate_pct', 0):.1f}%"},
                {"metric": "Terminal Growth", "value": f"{assumptions.get('terminal_growth_pct', 0):.1f}%"},
            ],
            "config": {
                "columns": [
                    {"key": "metric", "label": "Metric"},
                    {"key": "value", "label": "Value"},
                ],
            },
        })

    return blocks


def _extract_portfolio_visualizations(
    args: Dict[str, Any],
    result: Dict[str, Any],
) -> List[VisualizationBlock]:
    """Extract visualizations from portfolio analysis results."""
    blocks: List[VisualizationBlock] = []

    # 1. Allocation pie chart
    holdings = result.get("holdings", [])
    if holdings:
        blocks.append({
            "type": "pie_chart",
            "title": "Portfolio Allocation",
            "data": [
                {"name": h["ticker"], "value": h["weight_pct"]}
                for h in holdings
            ],
            "config": {"valueLabel": "Weight %"},
        })

    # 2. Holdings performance comparison → bar chart
    if holdings and any("annualized_return_pct" in h for h in holdings):
        perf_data = [
            {
                "ticker": h["ticker"],
                "return": h.get("annualized_return_pct", 0),
                "volatility": h.get("annualized_volatility_pct", 0),
            }
            for h in holdings
        ]
        blocks.append({
            "type": "bar_chart",
            "title": "Holdings — Return vs. Volatility",
            "data": perf_data,
            "config": {
                "xKey": "ticker",
                "bars": [
                    {"dataKey": "return", "label": "Ann. Return %"},
                    {"dataKey": "volatility", "label": "Ann. Volatility %"},
                ],
            },
        })

    # 3. Correlation heatmap
    corr = result.get("correlation_matrix", {})
    if corr and len(corr) > 1:
        tickers = list(corr.keys())
        rows = []
        for t in tickers:
            row: Dict[str, Any] = {"ticker": t}
            for t2 in tickers:
                row[t2] = round(corr[t].get(t2, 0), 2)
            rows.append(row)

        blocks.append({
            "type": "heatmap",
            "title": "Correlation Matrix",
            "data": rows,
            "config": {
                "rowKey": "ticker",
                "columns": tickers,
                "minValue": -1,
                "maxValue": 1,
            },
        })

    # 4. Portfolio risk summary → table
    portfolio_metrics = result.get("portfolio", {})
    benchmark = result.get("benchmark")
    if portfolio_metrics:
        summary_rows = [
            {"metric": "Ann. Return", "portfolio": f"{portfolio_metrics.get('annualized_return_pct', 0):.2f}%"},
            {"metric": "Ann. Volatility", "portfolio": f"{portfolio_metrics.get('annualized_volatility_pct', 0):.2f}%"},
            {"metric": "Sharpe Ratio", "portfolio": f"{portfolio_metrics.get('sharpe_ratio', 'N/A')}"},
            {"metric": "Max Drawdown", "portfolio": f"{portfolio_metrics.get('max_drawdown_pct', 0):.2f}%"},
            {"metric": "Daily VaR (95%)", "portfolio": f"{portfolio_metrics.get('var_95_daily_pct', 0):.2f}%"},
        ]
        cols = [
            {"key": "metric", "label": "Metric"},
            {"key": "portfolio", "label": "Portfolio"},
        ]
        if benchmark:
            for row in summary_rows:
                metric_key = row["metric"].lower().replace(" ", "_").replace(".", "").replace("(", "").replace(")", "").replace("%", "pct")
                bm_val = benchmark.get(
                    {
                        "ann_return": "annualized_return_pct",
                        "ann_volatility": "annualized_volatility_pct",
                        "sharpe_ratio": "sharpe_ratio",
                        "max_drawdown": "max_drawdown_pct",
                        "daily_var_95pct": "var_95_daily_pct",
                    }.get(metric_key, ""),
                )
                row["benchmark"] = f"{bm_val}" if bm_val is not None else "—"
            cols.append({"key": "benchmark", "label": f"Benchmark ({benchmark.get('ticker', 'SPY')})"})

        blocks.append({
            "type": "table",
            "title": "Portfolio Risk Summary",
            "data": summary_rows,
            "config": {"columns": cols},
        })

    return blocks


def _extract_earnings_visualizations(
    args: Dict[str, Any],
    result: Dict[str, Any],
) -> List[VisualizationBlock]:
    """Extract visualizations from earnings summary results."""
    blocks: List[VisualizationBlock] = []
    ticker = result.get("ticker", args.get("ticker", ""))

    # 1. EPS history → bar chart with estimate vs actual
    quarters = result.get("quarters", [])
    if quarters:
        chart_data = []
        for q in reversed(quarters):  # chronological order
            entry: Dict[str, Any] = {"quarter": q.get("date", "?")}
            if q.get("eps_actual") is not None:
                entry["actual"] = q["eps_actual"]
            if q.get("eps_estimate") is not None:
                entry["estimate"] = q["eps_estimate"]
            chart_data.append(entry)

        blocks.append({
            "type": "bar_chart",
            "title": f"{ticker} — EPS: Estimate vs. Actual",
            "data": chart_data,
            "config": {
                "xKey": "quarter",
                "bars": [
                    {"dataKey": "estimate", "label": "Estimate"},
                    {"dataKey": "actual", "label": "Actual"},
                ],
            },
        })

    # 2. Key metrics → table
    metrics = result.get("key_metrics", {})
    if metrics:
        rows = [
            {"metric": label, "value": _fmt_metric(metrics.get(key))}
            for key, label in [
                ("trailing_eps", "Trailing EPS"),
                ("forward_eps", "Forward EPS"),
                ("pe_trailing", "P/E (Trailing)"),
                ("pe_forward", "P/E (Forward)"),
                ("peg_ratio", "PEG Ratio"),
                ("earnings_growth_quarterly", "Qtr Earnings Growth"),
                ("revenue_growth", "Revenue Growth"),
            ]
        ]
        blocks.append({
            "type": "table",
            "title": f"{ticker} — Key Earnings Metrics",
            "data": rows,
            "config": {
                "columns": [
                    {"key": "metric", "label": "Metric"},
                    {"key": "value", "label": "Value"},
                ],
            },
        })

    return blocks


def _extract_screener_visualizations(
    args: Dict[str, Any],
    result: Dict[str, Any],
) -> List[VisualizationBlock]:
    """Extract visualizations from stock screener results."""
    blocks: List[VisualizationBlock] = []

    results_list = result.get("results", [])
    if not results_list:
        return blocks

    # 1. Screener results → table
    columns = [
        {"key": "ticker", "label": "Ticker"},
        {"key": "name", "label": "Name"},
        {"key": "price", "label": "Price"},
        {"key": "market_cap", "label": "Mkt Cap"},
        {"key": "pe_trailing", "label": "P/E"},
        {"key": "dividend_yield_pct", "label": "Div Yield %"},
    ]
    formatted = []
    for r in results_list:
        formatted.append({
            "ticker": r.get("ticker", ""),
            "name": r.get("name", ""),
            "price": f"${r['price']:,.2f}" if r.get("price") is not None else "—",
            "market_cap": _fmt_market_cap(r.get("market_cap")),
            "pe_trailing": f"{r['pe_trailing']:.1f}" if r.get("pe_trailing") is not None else "—",
            "dividend_yield_pct": f"{r['dividend_yield_pct']:.2f}%" if r.get("dividend_yield_pct") is not None else "—",
        })

    blocks.append({
        "type": "table",
        "title": f"Screener Results ({result.get('matches', len(results_list))} / {result.get('screened', '?')} matched)",
        "data": formatted,
        "config": {"columns": columns},
    })

    # 2. Market cap comparison → bar chart (if multiple results)
    if len(results_list) > 1:
        cap_data = [
            {
                "ticker": r["ticker"],
                "market_cap_b": round(r["market_cap"] / 1e9, 2) if r.get("market_cap") else 0,
            }
            for r in results_list
            if r.get("market_cap")
        ]
        if cap_data:
            blocks.append({
                "type": "bar_chart",
                "title": "Market Cap Comparison ($B)",
                "data": cap_data,
                "config": {
                    "xKey": "ticker",
                    "bars": [{"dataKey": "market_cap_b", "label": "Market Cap ($B)"}],
                },
            })

    return blocks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_metric(val: Any) -> str:
    if val is None:
        return "—"
    if isinstance(val, float):
        return f"{val:.2f}"
    return str(val)


def _fmt_market_cap(val: Any) -> str:
    if val is None:
        return "—"
    if val >= 1e12:
        return f"${val / 1e12:.2f}T"
    if val >= 1e9:
        return f"${val / 1e9:.2f}B"
    if val >= 1e6:
        return f"${val / 1e6:.1f}M"
    return f"${val:,.0f}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_EXTRACTORS = {
    "dcf_calculator": _extract_dcf_visualizations,
    "portfolio_analyzer": _extract_portfolio_visualizations,
    "earnings_summarizer": _extract_earnings_visualizations,
    "stock_screener": _extract_screener_visualizations,
}


def extract_visualizations(
    tool_name: str,
    tool_args: Dict[str, Any],
    tool_result: Dict[str, Any],
) -> List[VisualizationBlock]:
    """Extract visualization blocks from a tool execution result.

    Returns an empty list for unknown tools or when no visualizations
    can be generated.
    """
    extractor = _EXTRACTORS.get(tool_name)
    if not extractor:
        return []

    try:
        return extractor(tool_args, tool_result)
    except Exception:
        logger.debug("visualization_extraction_failed", tool=tool_name)
        return []
