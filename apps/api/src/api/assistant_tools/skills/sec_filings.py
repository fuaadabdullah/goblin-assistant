"""SEC filing intelligence tools."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...services.financial_guardrails import safe_skill
from ...services.sec_filings_service import sec_filing_service
from ..registry import ToolDefinition, ToolParameter, register_tool


@safe_skill
async def _handle_search_filings(
    query: str,
    filing_type: Optional[str] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    filing_types = [filing_type] if filing_type else None
    return sec_filing_service.search_filings(query=query, filing_types=filing_types, limit=limit)


@safe_skill
async def _handle_get_filing(
    query: str,
    filing_type: Optional[str] = None,
    accession_number: Optional[str] = None,
) -> Dict[str, Any]:
    return sec_filing_service.get_filing(
        query=query,
        filing_type=filing_type,
        accession_number=accession_number,
    )


@safe_skill
async def _handle_get_filing_section(
    query: str,
    section: str,
    filing_type: Optional[str] = None,
    accession_number: Optional[str] = None,
) -> Dict[str, Any]:
    return sec_filing_service.get_filing_section(
        query=query,
        section=section,
        filing_type=filing_type,
        accession_number=accession_number,
    )


@safe_skill
async def _handle_summarize_filing_section(
    query: str,
    section: str,
    filing_type: Optional[str] = None,
    accession_number: Optional[str] = None,
) -> Dict[str, Any]:
    return sec_filing_service.summarize_filing_section(
        query=query,
        section=section,
        filing_type=filing_type,
        accession_number=accession_number,
    )


register_tool(
    ToolDefinition(
        name="search_filings",
        description=(
            "Use when the user wants to find SEC filings for a company or ticker. "
            "Returns structured filing metadata including accession number, filing "
            "date, report date, document URL, and filing type."
        ),
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description=(
                    "Company name, ticker, or CIK to search in SEC filings. "
                    "Examples: AAPL, Microsoft, 320193."
                ),
            ),
            ToolParameter(
                name="filing_type",
                type="string",
                description="Optional filing type filter such as 10-K, 10-Q, 8-K, or 4.",
                required=False,
                enum=["10-K", "10-Q", "8-K", "4"],
                default=None,
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="Maximum filings to return (1-20). Defaults to 5.",
                required=False,
                default=5,
            ),
        ],
        handler=_handle_search_filings,
        category="finance",
    )
)

register_tool(
    ToolDefinition(
        name="get_filing",
        description=(
            "Use when the user wants the latest or specific SEC filing metadata "
            "for a company or ticker."
        ),
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="Company name, ticker, or CIK to resolve.",
            ),
            ToolParameter(
                name="filing_type",
                type="string",
                description="Optional filing type such as 10-K, 10-Q, 8-K, or 4.",
                required=False,
                enum=["10-K", "10-Q", "8-K", "4"],
                default=None,
            ),
            ToolParameter(
                name="accession_number",
                type="string",
                description="Optional accession number to select a specific filing.",
                required=False,
                default=None,
            ),
        ],
        handler=_handle_get_filing,
        category="finance",
    )
)

register_tool(
    ToolDefinition(
        name="get_filing_section",
        description=(
            "Use when the user wants a specific section from an SEC filing, "
            "such as Risk Factors, MD&A, or a Form 8-K item."
        ),
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="Company name, ticker, or CIK to resolve.",
            ),
            ToolParameter(
                name="section",
                type="string",
                description="Section name to extract, such as risk factors or item 1.01.",
            ),
            ToolParameter(
                name="filing_type",
                type="string",
                description="Optional filing type such as 10-K, 10-Q, 8-K, or 4.",
                required=False,
                enum=["10-K", "10-Q", "8-K", "4"],
                default=None,
            ),
            ToolParameter(
                name="accession_number",
                type="string",
                description="Optional accession number to select a specific filing.",
                required=False,
                default=None,
            ),
        ],
        handler=_handle_get_filing_section,
        category="finance",
    )
)

register_tool(
    ToolDefinition(
        name="summarize_filing_section",
        description=(
            "Use when the user wants a concise summary of a specific SEC filing "
            "section. Returns the extracted section text plus a short summary "
            "and key points."
        ),
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="Company name, ticker, or CIK to resolve.",
            ),
            ToolParameter(
                name="section",
                type="string",
                description="Section name to summarize, such as risk factors or MD&A.",
            ),
            ToolParameter(
                name="filing_type",
                type="string",
                description="Optional filing type such as 10-K, 10-Q, 8-K, or 4.",
                required=False,
                enum=["10-K", "10-Q", "8-K", "4"],
                default=None,
            ),
            ToolParameter(
                name="accession_number",
                type="string",
                description="Optional accession number to select a specific filing.",
                required=False,
                default=None,
            ),
        ],
        handler=_handle_summarize_filing_section,
        category="finance",
    )
)
