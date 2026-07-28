"""DCF valuation visualization extractor."""

from typing import Any, Dict, List

from .types import VisualizationBlock


def extract_dcf_visualizations(
    args: Dict[str, Any],
    result: Dict[str, Any],
) -> List[VisualizationBlock]:
    """Extract visualizations from a DCF valuation result."""
    blocks: List[VisualizationBlock] = []
    ticker = result.get("ticker", args.get("ticker", ""))

    # 1. FCF projections -> bar chart
    projections = result.get("projections", [])
    if projections:
        blocks.append(
            {
                "type": "bar_chart",
                "title": f"{ticker} \u2014 Projected Free Cash Flow",
                "data": [
                    {"year": f"Year {p['year']}", "fcf": p["projected_fcf"]} for p in projections
                ],
                "config": {
                    "xKey": "year",
                    "bars": [{"dataKey": "fcf", "label": "FCF ($)"}],
                },
            }
        )

    # 2. Sensitivity matrix -> table
    matrix = result.get("sensitivity_matrix", [])
    if matrix:
        growth_keys = [k for k in matrix[0] if k.startswith("growth_")]
        columns = [
            {"key": "wacc_pct", "label": "WACC %"},
            *[{"key": k, "label": f"Growth {k.replace('growth_', '')}%"} for k in growth_keys],
        ]
        blocks.append(
            {
                "type": "table",
                "title": f"{ticker} \u2014 Sensitivity Analysis (Price per Share)",
                "data": matrix,
                "config": {
                    "columns": columns,
                    "highlight": {
                        "key": "wacc_pct",
                        "value": result.get("assumptions", {}).get("wacc_pct"),
                    },
                },
            }
        )

    # 3. Valuation summary -> table
    valuation = result.get("valuation", {})
    assumptions = result.get("assumptions", {})
    if valuation:
        blocks.append(
            {
                "type": "table",
                "title": f"{ticker} \u2014 DCF Valuation Summary",
                "data": [
                    {
                        "metric": "Intrinsic Value / Share",
                        "value": f"${valuation.get('intrinsic_value_per_share', 0):,.2f}",
                    },
                    {
                        "metric": "Current Price",
                        "value": f"${valuation.get('current_price', 0):,.2f}",
                    },
                    {
                        "metric": "Upside",
                        "value": (
                            f"{valuation.get('upside_pct', 0):.1f}%"
                            if valuation.get("upside_pct") is not None
                            else "N/A"
                        ),
                    },
                    {
                        "metric": "WACC",
                        "value": f"{assumptions.get('wacc_pct', 0):.1f}%",
                    },
                    {
                        "metric": "Growth Rate",
                        "value": f"{assumptions.get('growth_rate_pct', 0):.1f}%",
                    },
                    {
                        "metric": "Terminal Growth",
                        "value": f"{assumptions.get('terminal_growth_pct', 0):.1f}%",
                    },
                ],
                "config": {
                    "columns": [
                        {"key": "metric", "label": "Metric"},
                        {"key": "value", "label": "Value"},
                    ],
                },
            }
        )

    return blocks
