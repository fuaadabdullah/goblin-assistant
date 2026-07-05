"""Stock screener visualization extractor."""

from typing import Any, Dict, List

from .formatters import fmt_market_cap
from .types import VisualizationBlock


def extract_screener_visualizations(
    args: Dict[str, Any],
    result: Dict[str, Any],
) -> List[VisualizationBlock]:
    """Extract visualizations from stock screener results."""
    blocks: List[VisualizationBlock] = []

    results_list = result.get("results", [])
    if not results_list:
        return blocks

    # 1. Screener results -> table
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
        formatted.append(
            {
                "ticker": r.get("ticker", ""),
                "name": r.get("name", ""),
                "price": f"${r['price']:,.2f}" if r.get("price") is not None else "—",
                "market_cap": fmt_market_cap(r.get("market_cap")),
                "pe_trailing": (
                    f"{r['pe_trailing']:.1f}" if r.get("pe_trailing") is not None else "—"
                ),
                "dividend_yield_pct": (
                    f"{r['dividend_yield_pct']:.2f}%"
                    if r.get("dividend_yield_pct") is not None
                    else "—"
                ),
            }
        )

    blocks.append(
        {
            "type": "table",
            "title": f"Screener Results ({result.get('matches', len(results_list))} / {result.get('screened', '?')} matched)",
            "data": formatted,
            "config": {"columns": columns},
        }
    )

    # 2. Market cap comparison -> bar chart (if multiple results)
    if len(results_list) > 1:
        cap_data = [
            {
                "ticker": r["ticker"],
                "market_cap_b": (round(r["market_cap"] / 1e9, 2) if r.get("market_cap") else 0),
            }
            for r in results_list
            if r.get("market_cap")
        ]
        if cap_data:
            blocks.append(
                {
                    "type": "bar_chart",
                    "title": "Market Cap Comparison ($B)",
                    "data": cap_data,
                    "config": {
                        "xKey": "ticker",
                        "bars": [{"dataKey": "market_cap_b", "label": "Market Cap ($B)"}],
                    },
                }
            )

    return blocks
