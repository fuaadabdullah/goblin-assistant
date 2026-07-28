"""
Visualization extractors package.

Each extractor module maps a tool name to a function that transforms
tool execution results into chart-ready data structures for the frontend.
"""

from typing import Any, Dict, List

import structlog

from .dcf_extractor import extract_dcf_visualizations
from .earnings_extractor import extract_earnings_visualizations
from .portfolio_extractor import extract_portfolio_visualizations
from .screener_extractor import extract_screener_visualizations
from .types import VisualizationBlock

logger = structlog.get_logger(__name__)

_EXTRACTORS = {
    "dcf_calculator": extract_dcf_visualizations,
    "portfolio_analyzer": extract_portfolio_visualizations,
    "earnings_summarizer": extract_earnings_visualizations,
    "stock_screener": extract_screener_visualizations,
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


__all__ = [
    "extract_visualizations",
    "VisualizationBlock",
]
