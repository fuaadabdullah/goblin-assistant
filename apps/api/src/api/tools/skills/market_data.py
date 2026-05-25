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
        "Use when the user asks for a live or latest single-stock quote, "
        "price move, volume, market cap, or basic market snapshot. Returns "
        "current quote fields for one public ticker; not for historical "
        "charts, financial statements, ratios, or earnings history."
    ),
    parameters=[
        ToolParameter(
            name="ticker",
            type="string",
            description=(
                "Public equity ticker symbol, uppercase when possible, such "
                "as AAPL, MSFT, TSLA, BRK.B, or GOOGL."
            ),
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
        "Use when the user asks for historical prices, OHLCV candles, "
        "charts, trend analysis, returns over time, or backtesting inputs "
        "for one stock. Returns dated open, high, low, close, and volume "
        "rows for the requested period and interval."
    ),
    parameters=[
        ToolParameter(
            name="ticker",
            type="string",
            description=(
                "Public equity ticker symbol to fetch history for, such as "
                "AAPL, MSFT, NVDA, or SPY."
            ),
        ),
        ToolParameter(
            name="period",
            type="string",
            description=(
                "Lookback range for returned history. Use 1d or 5d for "
                "intraday requests, 1mo-5y for fixed lookbacks, ytd for "
                "year-to-date, or max for all available history. Default: 1y."
            ),
            required=False,
            enum=["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"],
            default="1y",
        ),
        ToolParameter(
            name="interval",
            type="string",
            description=(
                "Candle interval. Use 1m-1h only for short intraday windows; "
                "use 1d, 1wk, or 1mo for daily or longer analysis. Default: 1d."
            ),
            required=False,
            enum=["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"],
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
        "Use when the user asks for company fundamentals from financial "
        "statements, such as revenue, net income, EBITDA, free cash flow, "
        "cash, debt, shares outstanding, or balance-sheet context. Returns "
        "latest available statement-style metrics for one ticker."
    ),
    parameters=[
        ToolParameter(
            name="ticker",
            type="string",
            description="Public equity ticker symbol for the company, such as AAPL or MSFT.",
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
        "Use when the user asks for raw earnings data, EPS, upcoming or "
        "recent earnings dates, estimates versus actuals, or surprise "
        "percentages. Returns earnings fields for one ticker; use "
        "earnings_summarizer when the user wants a narrative or verdict."
    ),
    parameters=[
        ToolParameter(
            name="ticker",
            type="string",
            description="Public equity ticker symbol for earnings data, such as NVDA or AAPL.",
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
        "Use when the user asks for valuation, profitability, leverage, "
        "dividend, risk, margin, or 52-week range ratios for one stock. "
        "Returns metrics such as P/E, P/B, EV/EBITDA, debt/equity, ROE, "
        "ROA, margins, dividend yield, beta, and 52-week high/low."
    ),
    parameters=[
        ToolParameter(
            name="ticker",
            type="string",
            description="Public equity ticker symbol for ratio lookup, such as MSFT or JPM.",
        ),
    ],
    handler=_handle_get_key_ratios,
))
