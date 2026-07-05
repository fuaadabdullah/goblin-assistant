"""Portfolio analysis visualization extractor."""

from typing import Any, Dict, List

from .types import VisualizationBlock


def extract_portfolio_visualizations(
    args: Dict[str, Any],
    result: Dict[str, Any],
) -> List[VisualizationBlock]:
    """Extract visualizations from portfolio analysis results."""
    blocks: List[VisualizationBlock] = []

    # 1. Allocation pie chart
    holdings = result.get("holdings", [])
    if holdings:
        blocks.append(
            {
                "type": "pie_chart",
                "title": "Portfolio Allocation",
                "data": [{"name": h["ticker"], "value": h["weight_pct"]} for h in holdings],
                "config": {"valueLabel": "Weight %"},
            }
        )

    # 2. Holdings performance comparison -> bar chart
    if holdings and any("annualized_return_pct" in h for h in holdings):
        perf_data = [
            {
                "ticker": h["ticker"],
                "return": h.get("annualized_return_pct", 0),
                "volatility": h.get("annualized_volatility_pct", 0),
            }
            for h in holdings
        ]
        blocks.append(
            {
                "type": "bar_chart",
                "title": "Holdings - Return vs. Volatility",
                "data": perf_data,
                "config": {
                    "xKey": "ticker",
                    "bars": [
                        {"dataKey": "return", "label": "Ann. Return %"},
                        {"dataKey": "volatility", "label": "Ann. Volatility %"},
                    ],
                },
            }
        )

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

        blocks.append(
            {
                "type": "heatmap",
                "title": "Correlation Matrix",
                "data": rows,
                "config": {
                    "rowKey": "ticker",
                    "columns": tickers,
                    "minValue": -1,
                    "maxValue": 1,
                },
            }
        )

    # 4. Portfolio risk summary -> table
    portfolio_metrics = result.get("portfolio", {})
    benchmark = result.get("benchmark")
    if portfolio_metrics:
        summary_rows = [
            {
                "metric": "Ann. Return",
                "portfolio": f"{portfolio_metrics.get('annualized_return_pct', 0):.2f}%",
            },
            {
                "metric": "Ann. Volatility",
                "portfolio": f"{portfolio_metrics.get('annualized_volatility_pct', 0):.2f}%",
            },
            {
                "metric": "Sharpe Ratio",
                "portfolio": f"{portfolio_metrics.get('sharpe_ratio', 'N/A')}",
            },
            {
                "metric": "Max Drawdown",
                "portfolio": f"{portfolio_metrics.get('max_drawdown_pct', 0):.2f}%",
            },
            {
                "metric": "Daily VaR (95%)",
                "portfolio": f"{portfolio_metrics.get('var_95_daily_pct', 0):.2f}%",
            },
        ]
        cols = [
            {"key": "metric", "label": "Metric"},
            {"key": "portfolio", "label": "Portfolio"},
        ]
        if benchmark:
            for row in summary_rows:
                metric_key = (
                    row["metric"]
                    .lower()
                    .replace(" ", "_")
                    .replace(".", "")
                    .replace("(", "")
                    .replace(")", "")
                    .replace("%", "pct")
                )
                bm_val = benchmark.get(
                    {
                        "ann_return": "annualized_return_pct",
                        "ann_volatility": "annualized_volatility_pct",
                        "sharpe_ratio": "sharpe_ratio",
                        "max_drawdown": "max_drawdown_pct",
                        "daily_var_95pct": "var_95_daily_pct",
                    }.get(metric_key, ""),
                )
                row["benchmark"] = f"{bm_val}" if bm_val is not None else "-"
            cols.append(
                {
                    "key": "benchmark",
                    "label": f"Benchmark ({benchmark.get('ticker', 'SPY')})",
                }
            )

        blocks.append(
            {
                "type": "table",
                "title": "Portfolio Risk Summary",
                "data": summary_rows,
                "config": {"columns": cols},
            }
        )

    return blocks
