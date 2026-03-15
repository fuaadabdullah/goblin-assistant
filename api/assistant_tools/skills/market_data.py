"""
Market data tools for Goblin Assistant.

Registers tools for fetching live financial data (quotes, price history,
financials, earnings, key ratios) via the FinancialDataService.
These tool definitions are exported in OpenAI function-calling format
so the LLM can invoke them natively.
"""

from __future__ import annotations

from ..registry import ToolDefinition, ToolParameter, register_tool
from ...services.financial_data_service import financial_data_service


# ---------------------------------------------------------------------------
# get_stock_quote
# ---------------------------------------------------------------------------

async def _handle_get_stock_quote(ticker: str) -> dict:
    return await financial_data_service.get_current_quote(ticker)

register_tool(ToolDefinition(
    name="get_stock_quote",
    description=(
        "Get the current stock quote for a ticker symbol. Returns price, "
        "change, volume, market cap, and other basic market data."
    ),
    parameters=[
        ToolParameter(
            name="ticker",
            type="string",
            description="Stock ticker symbol, e.g. AAPL, MSFT, TSLA",
        ),
    ],
    handler=_handle_get_stock_quote,
))


# ---------------------------------------------------------------------------
# get_price_history
# ---------------------------------------------------------------------------

async def _handle_get_price_history(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> dict:
    return await financial_data_service.get_price_history(ticker, period, interval)

register_tool(ToolDefinition(
    name="get_price_history",
    description=(
        "Get historical price data (OHLCV) for a stock ticker. "
        "Useful for charting, backtesting, and trend analysis."
    ),
    parameters=[
        ToolParameter(
            name="ticker",
            type="string",
            description="Stock ticker symbol, e.g. AAPL",
        ),
        ToolParameter(
            name="period",
            type="string",
            description="Time period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, ytd, max",
            required=False,
            default="1y",
        ),
        ToolParameter(
            name="interval",
            type="string",
            description="Data interval: 1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo",
            required=False,
            default="1d",
        ),
    ],
    handler=_handle_get_price_history,
))


# ---------------------------------------------------------------------------
# get_financials
# ---------------------------------------------------------------------------

async def _handle_get_financials(ticker: str) -> dict:
    return await financial_data_service.get_financials(ticker)

register_tool(ToolDefinition(
    name="get_financials",
    description=(
        "Get key financial data for a company: revenue, net income, EBITDA, "
        "free cash flow, total cash/debt, and balance sheet items."
    ),
    parameters=[
        ToolParameter(
            name="ticker",
            type="string",
            description="Stock ticker symbol, e.g. AAPL",
        ),
    ],
    handler=_handle_get_financials,
))


# ---------------------------------------------------------------------------
# get_earnings
# ---------------------------------------------------------------------------

async def _handle_get_earnings(ticker: str) -> dict:
    return await financial_data_service.get_earnings(ticker)

register_tool(ToolDefinition(
    name="get_earnings",
    description=(
        "Get earnings data for a stock: trailing/forward EPS, recent quarterly "
        "earnings dates with actual vs estimate EPS, and surprise percentages."
    ),
    parameters=[
        ToolParameter(
            name="ticker",
            type="string",
            description="Stock ticker symbol, e.g. NVDA",
        ),
    ],
    handler=_handle_get_earnings,
))


# ---------------------------------------------------------------------------
# get_key_ratios
# ---------------------------------------------------------------------------

async def _handle_get_key_ratios(ticker: str) -> dict:
    return await financial_data_service.get_key_ratios(ticker)

register_tool(ToolDefinition(
    name="get_key_ratios",
    description=(
        "Get key financial ratios for a stock: P/E, P/B, EV/EBITDA, "
        "debt/equity, ROE, ROA, profit margins, dividend yield, beta, "
        "and 52-week high/low."
    ),
    parameters=[
        ToolParameter(
            name="ticker",
            type="string",
            description="Stock ticker symbol, e.g. MSFT",
        ),
    ],
    handler=_handle_get_key_ratios,
))
