"""Earnings summary visualization extractor."""

from typing import Any, Dict, List

from .formatters import fmt_metric
from .types import VisualizationBlock


def extract_earnings_visualizations(
    args: Dict[str, Any],
    result: Dict[str, Any],
) -> List[VisualizationBlock]:
    """Extract visualizations from earnings summary results."""
    blocks: List[VisualizationBlock] = []
    ticker = result.get("ticker", args.get("ticker", ""))

    # 1. EPS history -> bar chart with estimate vs actual
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

        blocks.append(
            {
                "type": "bar_chart",
                "title": f"{ticker} - EPS: Estimate vs. Actual",
                "data": chart_data,
                "config": {
                    "xKey": "quarter",
                    "bars": [
                        {"dataKey": "estimate", "label": "Estimate"},
                        {"dataKey": "actual", "label": "Actual"},
                    ],
                },
            }
        )

    # 2. Key metrics -> table
    metrics = result.get("key_metrics", {})
    if metrics:
        rows = [
            {"metric": label, "value": fmt_metric(metrics.get(key))}
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
        blocks.append(
            {
                "type": "table",
                "title": f"{ticker} - Key Earnings Metrics",
                "data": rows,
                "config": {
                    "columns": [
                        {"key": "metric", "label": "Metric"},
                        {"key": "value", "label": "Value"},
                    ],
                },
            }
        )

    return blocks
