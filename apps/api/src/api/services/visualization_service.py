"""
Visualization extraction service.

Compatibility facade over the dedicated visualization extractors package.
Preserves the public API surface for existing callers.

The implementation lives in focused modules under `visualization/`:
  dcf_extractor.py       - DCF valuation visualizations
  portfolio_extractor.py - Portfolio analysis visualizations
  earnings_extractor.py  - Earnings summary visualizations
  screener_extractor.py  - Stock screener visualizations
  formatters.py          - Formatting helpers
  types.py               - Type aliases
"""

from __future__ import annotations

from .visualization import extract_visualizations as _extract_visualizations
from .visualization.dcf_extractor import (
    extract_dcf_visualizations as dcf_visualizations,
)
from .visualization.earnings_extractor import (
    extract_earnings_visualizations as earnings_visualizations,
)
from .visualization.formatters import fmt_market_cap, fmt_metric
from .visualization.portfolio_extractor import (
    extract_portfolio_visualizations as portfolio_visualizations,
)
from .visualization.screener_extractor import (
    extract_screener_visualizations as screener_visualizations,
)
from .visualization.types import VisualizationBlock

# Re-export both public and backward-compatible private APIs
extract_visualizations = _extract_visualizations
_extract_dcf_visualizations = dcf_visualizations
_extract_portfolio_visualizations = portfolio_visualizations
_extract_earnings_visualizations = earnings_visualizations
_extract_screener_visualizations = screener_visualizations
_fmt_metric = fmt_metric
_fmt_market_cap = fmt_market_cap

__all__ = [
    "extract_visualizations",
    "VisualizationBlock",
    # backward-compatible private names used by tests
    "_extract_dcf_visualizations",
    "_extract_portfolio_visualizations",
    "_extract_earnings_visualizations",
    "_extract_screener_visualizations",
    "_fmt_metric",
    "_fmt_market_cap",
]
