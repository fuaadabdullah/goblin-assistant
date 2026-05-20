"""
Financial data service for Goblin Assistant.

Unified wrapper over yfinance (primary) with Redis caching.
All public methods are async-safe via asyncio.to_thread for the
synchronous yfinance library.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Ticker validation
# ---------------------------------------------------------------------------

_TICKER_RE = re.compile(r"^[A-Z]{1,5}(\.[A-Z]{1,2})?$")


def _validate_ticker(ticker: str) -> str:
    """Sanitize and validate a stock ticker symbol."""
    cleaned = ticker.strip().upper()
    if not _TICKER_RE.match(cleaned):
        raise ValueError(f"Invalid ticker symbol: {ticker!r}")
    return cleaned


# ---------------------------------------------------------------------------
# Redis cache helpers
# ---------------------------------------------------------------------------

_CACHE_PREFIX = "fin:"
_QUOTE_TTL = 60 * 15       # 15 minutes
_FINANCIALS_TTL = 60 * 60 * 24  # 24 hours
_EARNINGS_TTL = 60 * 60 * 24
_RATIOS_TTL = 60 * 60 * 24
_HISTORY_TTL = 60 * 60      # 1 hour


def _get_redis():
    """Return a Redis client or None when unavailable."""
    try:
        import redis as _redis
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        return _redis.from_url(url, decode_responses=True, socket_connect_timeout=2)
    except Exception:
        return None


def _cache_get(key: str) -> Optional[Dict[str, Any]]:
    try:
        client = _get_redis()
        if client is None:
            return None
        raw = client.get(f"{_CACHE_PREFIX}{key}")
        return json.loads(raw) if raw else None
    except Exception:
        return None


def _cache_set(key: str, value: Dict[str, Any], ttl: int) -> None:
    try:
        client = _get_redis()
        if client is None:
            return
        client.setex(f"{_CACHE_PREFIX}{key}", ttl, json.dumps(value, default=str))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# yfinance wrappers (sync — called via asyncio.to_thread)
# ---------------------------------------------------------------------------


def _yf_get_quote(ticker: str) -> Dict[str, Any]:
    import yfinance as yf

    t = yf.Ticker(ticker)
    info = t.info
    return {
        "ticker": ticker,
        "name": info.get("shortName") or info.get("longName", ticker),
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "previous_close": info.get("previousClose"),
        "change": info.get("regularMarketChange"),
        "change_percent": info.get("regularMarketChangePercent"),
        "volume": info.get("volume") or info.get("regularMarketVolume"),
        "market_cap": info.get("marketCap"),
        "currency": info.get("currency", "USD"),
        "exchange": info.get("exchange"),
        "fetched_at": datetime.utcnow().isoformat(),
    }


def _yf_get_price_history(
    ticker: str, period: str, interval: str
) -> Dict[str, Any]:
    import yfinance as yf

    t = yf.Ticker(ticker)
    df = t.history(period=period, interval=interval)
    if df.empty:
        return {"ticker": ticker, "period": period, "interval": interval, "data": []}

    records = []
    for date, row in df.iterrows():
        records.append({
            "date": str(date.date()) if hasattr(date, "date") else str(date),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
        })

    return {
        "ticker": ticker,
        "period": period,
        "interval": interval,
        "data_points": len(records),
        "data": records,
    }


def _yf_get_financials(ticker: str) -> Dict[str, Any]:
    import yfinance as yf

    t = yf.Ticker(ticker)
    info = t.info

    # Income statement items
    result: Dict[str, Any] = {
        "ticker": ticker,
        "revenue": info.get("totalRevenue"),
        "net_income": info.get("netIncomeToCommon"),
        "ebitda": info.get("ebitda"),
        "gross_profit": info.get("grossProfits"),
        "operating_income": info.get("operatingIncome"),
        "free_cash_flow": info.get("freeCashflow"),
        "operating_cash_flow": info.get("operatingCashflow"),
        "total_cash": info.get("totalCash"),
        "total_debt": info.get("totalDebt"),
        "total_assets": info.get("totalAssets"),
        "book_value": info.get("bookValue"),
        "shares_outstanding": info.get("sharesOutstanding"),
        "currency": info.get("currency", "USD"),
        "fetched_at": datetime.utcnow().isoformat(),
    }
    return result


def _yf_get_earnings(ticker: str) -> Dict[str, Any]:
    import yfinance as yf

    t = yf.Ticker(ticker)
    info = t.info

    earnings_dates = []
    try:
        ed = t.earnings_dates
        if ed is not None and not ed.empty:
            for date, row in ed.head(8).iterrows():
                earnings_dates.append({
                    "date": str(date.date()) if hasattr(date, "date") else str(date),
                    "eps_estimate": _safe_float(row.get("EPS Estimate")),
                    "eps_actual": _safe_float(row.get("Reported EPS")),
                    "surprise_percent": _safe_float(row.get("Surprise(%)")),
                })
    except Exception:
        pass

    return {
        "ticker": ticker,
        "trailing_eps": info.get("trailingEps"),
        "forward_eps": info.get("forwardEps"),
        "peg_ratio": info.get("pegRatio"),
        "earnings_quarterly_growth": info.get("earningsQuarterlyGrowth"),
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_dates": earnings_dates,
        "fetched_at": datetime.utcnow().isoformat(),
    }


def _yf_get_key_ratios(ticker: str) -> Dict[str, Any]:
    import yfinance as yf

    t = yf.Ticker(ticker)
    info = t.info

    return {
        "ticker": ticker,
        "pe_trailing": info.get("trailingPE"),
        "pe_forward": info.get("forwardPE"),
        "pb_ratio": info.get("priceToBook"),
        "ps_ratio": info.get("priceToSalesTrailing12Months"),
        "ev_ebitda": info.get("enterpriseToEbitda"),
        "ev_revenue": info.get("enterpriseToRevenue"),
        "debt_to_equity": info.get("debtToEquity"),
        "current_ratio": info.get("currentRatio"),
        "roe": info.get("returnOnEquity"),
        "roa": info.get("returnOnAssets"),
        "profit_margin": info.get("profitMargins"),
        "operating_margin": info.get("operatingMargins"),
        "dividend_yield": info.get("dividendYield"),
        "payout_ratio": info.get("payoutRatio"),
        "beta": info.get("beta"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "fetched_at": datetime.utcnow().isoformat(),
    }


def _safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        import math
        return None if math.isnan(f) else round(f, 4)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------


class FinancialDataService:
    """Async-safe financial data service with caching, rate limiting, and timeouts."""

    async def get_current_quote(self, ticker: str) -> Dict[str, Any]:
        from .financial_guardrails import check_rate_limit, with_timeout

        ticker = _validate_ticker(ticker)
        cached = _cache_get(f"quote:{ticker}")
        if cached:
            cached["_cached"] = True
            return cached

        check_rate_limit()
        result = await with_timeout(
            asyncio.to_thread(_yf_get_quote, ticker), ticker=ticker,
        )
        _cache_set(f"quote:{ticker}", result, _QUOTE_TTL)
        return result

    async def get_price_history(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> Dict[str, Any]:
        from .financial_guardrails import check_rate_limit, with_timeout

        ticker = _validate_ticker(ticker)
        allowed_periods = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"}
        allowed_intervals = {"1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"}
        if period not in allowed_periods:
            period = "1y"
        if interval not in allowed_intervals:
            interval = "1d"

        cache_key = f"hist:{ticker}:{period}:{interval}"
        cached = _cache_get(cache_key)
        if cached:
            cached["_cached"] = True
            return cached

        check_rate_limit()
        result = await with_timeout(
            asyncio.to_thread(_yf_get_price_history, ticker, period, interval),
            ticker=ticker,
        )
        _cache_set(cache_key, result, _HISTORY_TTL)
        return result

    async def get_financials(self, ticker: str) -> Dict[str, Any]:
        from .financial_guardrails import check_rate_limit, with_timeout

        ticker = _validate_ticker(ticker)
        cached = _cache_get(f"fin:{ticker}")
        if cached:
            cached["_cached"] = True
            return cached

        check_rate_limit()
        result = await with_timeout(
            asyncio.to_thread(_yf_get_financials, ticker), ticker=ticker,
        )
        _cache_set(f"fin:{ticker}", result, _FINANCIALS_TTL)
        return result

    async def get_earnings(self, ticker: str) -> Dict[str, Any]:
        from .financial_guardrails import check_rate_limit, with_timeout

        ticker = _validate_ticker(ticker)
        cached = _cache_get(f"earn:{ticker}")
        if cached:
            cached["_cached"] = True
            return cached

        check_rate_limit()
        result = await with_timeout(
            asyncio.to_thread(_yf_get_earnings, ticker), ticker=ticker,
        )
        _cache_set(f"earn:{ticker}", result, _EARNINGS_TTL)
        return result

    async def get_key_ratios(self, ticker: str) -> Dict[str, Any]:
        from .financial_guardrails import check_rate_limit, with_timeout

        ticker = _validate_ticker(ticker)
        cached = _cache_get(f"ratios:{ticker}")
        if cached:
            cached["_cached"] = True
            return cached

        check_rate_limit()
        result = await with_timeout(
            asyncio.to_thread(_yf_get_key_ratios, ticker), ticker=ticker,
        )
        _cache_set(f"ratios:{ticker}", result, _RATIOS_TTL)
        return result


# Module-level singleton
financial_data_service = FinancialDataService()
