"""Formatting helpers for visualization values."""

from typing import Any


def fmt_metric(val: Any) -> str:
    """Format a metric value for display."""
    if val is None:
        return "\u2014"
    if isinstance(val, float):
        return f"{val:.2f}"
    return str(val)


def fmt_market_cap(val: Any) -> str:
    """Format a market cap value for display."""
    if val is None:
        return "\u2014"
    if val >= 1e12:
        return f"${val / 1e12:.2f}T"
    if val >= 1e9:
        return f"${val / 1e9:.2f}B"
    if val >= 1e6:
        return f"${val / 1e6:.1f}M"
    return f"${val:,.0f}"
