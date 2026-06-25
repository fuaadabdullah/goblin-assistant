"""
Financial data service for Goblin Assistant.

Unified wrapper over yfinance (primary) with Redis caching.
All public methods are async-safe via asyncio.to_thread for the
synchronous yfinance library.
"""

from __future__ import annotations

import asyncio
import html
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlsplit

import httpx
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
_QUOTE_TTL = 60 * 15  # 15 minutes
_FINANCIALS_TTL = 60 * 60 * 24  # 24 hours
_EARNINGS_TTL = 60 * 60 * 24
_RATIOS_TTL = 60 * 60 * 24
_HISTORY_TTL = 60 * 60  # 1 hour
_NEWS_TTL = 60 * 5
_GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
_NEWS_PUBLISHER_ALIASES = {
    "reuters": "Reuters",
    "ap": "AP News",
    "associated press": "AP News",
    "bloomberg": "Bloomberg",
    "cnbc": "CNBC",
    "yahoo finance": "Yahoo Finance",
    "marketwatch": "MarketWatch",
    "wsj": "Wall Street Journal",
    "wall street journal": "Wall Street Journal",
    "investing.com": "Investing.com",
    "business wire": "Business Wire",
    "pr newswire": "PR Newswire",
}
_NEWS_DOMAIN_ALIASES = {
    "reuters.com": "Reuters",
    "apnews.com": "AP News",
    "bloomberg.com": "Bloomberg",
    "cnbc.com": "CNBC",
    "finance.yahoo.com": "Yahoo Finance",
    "marketwatch.com": "MarketWatch",
    "wsj.com": "Wall Street Journal",
    "investing.com": "Investing.com",
    "businesswire.com": "Business Wire",
    "prnewswire.com": "PR Newswire",
}


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


def _yf_get_price_history(ticker: str, period: str, interval: str) -> Dict[str, Any]:
    import yfinance as yf

    t = yf.Ticker(ticker)
    df = t.history(period=period, interval=interval)
    if df.empty:
        return {"ticker": ticker, "period": period, "interval": interval, "data": []}

    records = []
    for date, row in df.iterrows():
        records.append(
            {
                "date": str(date.date()) if hasattr(date, "date") else str(date),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            }
        )

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
                earnings_dates.append(
                    {
                        "date": (str(date.date()) if hasattr(date, "date") else str(date)),
                        "eps_estimate": _safe_float(row.get("EPS Estimate")),
                        "eps_actual": _safe_float(row.get("Reported EPS")),
                        "surprise_percent": _safe_float(row.get("Surprise(%)")),
                    }
                )
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


def _strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", html.unescape(value or "")).strip()


def _extract_market_ticker(query: str) -> Optional[str]:
    cleaned = query.strip().upper()
    if not cleaned:
        return None

    # Prefer direct ticker-style tokens over the whole query.
    candidates = re.split(r"[^A-Z0-9.]+", cleaned)
    for candidate in candidates:
        token = candidate.strip()
        if not token:
            continue
        if _TICKER_RE.match(token):
            return token
    return None


def _normalize_news_publisher(source: str, link: str = "") -> str:
    raw = re.sub(r"\s+", " ", (source or "").strip())
    if not raw and link:
        raw = _domain_from_url(link)
    if not raw:
        return "Unknown"

    key = raw.lower()
    if key in _NEWS_PUBLISHER_ALIASES:
        return _NEWS_PUBLISHER_ALIASES[key]

    domain = _domain_from_url(link)
    if domain and domain in _NEWS_DOMAIN_ALIASES:
        return _NEWS_DOMAIN_ALIASES[domain]

    if raw.isupper() and len(raw) <= 6:
        return raw
    return raw.title()


def _domain_from_url(url: str) -> str:
    try:
        parsed = urlsplit(url.strip())
    except Exception:  # noqa: BLE001
        return ""

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    domain = parsed.netloc.lower().strip()
    return domain[4:] if domain.startswith("www.") else domain


def normalize_market_news_sources(query: str, sources: list[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize market news sources with optional ticker awareness."""

    query = query.strip()
    ticker = _extract_market_ticker(query)
    normalized_query = ticker or query
    normalized_sources = []

    for source in sources:
        title = str(source.get("title", "")).strip()
        link = str(source.get("url") or source.get("link") or "").strip()
        snippet = str(source.get("snippet") or source.get("abstract") or "").strip()
        publisher = _normalize_news_publisher(
            str(source.get("publisher") or source.get("source") or ""),
            link,
        )
        source_domain = _domain_from_url(link)
        normalized_item = {
            "title": title,
            "url": link,
            "snippet": snippet or title,
            "publisher": publisher,
            "source_domain": source_domain,
            "published_at": str(source.get("published_at") or source.get("pubDate") or "").strip(),
            "source": "google_news",
        }
        if ticker:
            normalized_item["ticker"] = ticker
            normalized_item["tickers"] = [ticker]
        elif source.get("ticker"):
            normalized_item["ticker"] = str(source.get("ticker")).strip().upper()
            normalized_item["tickers"] = [normalized_item["ticker"]]
        elif source.get("tickers"):
            normalized_item["tickers"] = [
                str(item).strip().upper() for item in source.get("tickers", []) if str(item).strip()
            ]
            if normalized_item["tickers"]:
                normalized_item["ticker"] = normalized_item["tickers"][0]
        normalized_sources.append(normalized_item)

    return {
        "query": query,
        "normalized_query": normalized_query,
        "ticker": ticker,
        "results": normalized_sources,
        "count": len(normalized_sources),
    }


def _fetch_market_news(query: str, limit: int) -> Dict[str, Any]:
    params = {
        "q": query,
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
    }

    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.get(_GOOGLE_NEWS_RSS, params=params)
            resp.raise_for_status()
            xml_text = resp.text
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Market news request failed: {exc}"}

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return {"error": f"Market news XML parse error: {exc}"}

    channel = root.find("channel")
    items = [] if channel is None else channel.findall("item")
    raw_results = []
    for item in items[:limit]:
        title_el = item.find("title")
        link_el = item.find("link")
        source_el = item.find("source")
        pub_date_el = item.find("pubDate")
        desc_el = item.find("description")

        title = (title_el.text or "").strip() if title_el is not None else ""
        link = (link_el.text or "").strip() if link_el is not None else ""
        source = (source_el.text or "").strip() if source_el is not None else ""
        published_at = (pub_date_el.text or "").strip() if pub_date_el is not None else ""
        summary = _strip_html(desc_el.text or "") if desc_el is not None else ""
        if not summary:
            summary = title

        if not title and not link:
            continue

        raw_results.append(
            {
                "title": title,
                "url": link,
                "snippet": summary,
                "publisher": source,
                "published_at": published_at,
                "source": "google_news",
            }
        )

    normalized = normalize_market_news_sources(query, raw_results)
    results = normalized["results"]
    return {
        "query": normalized["query"],
        "normalized_query": normalized["normalized_query"],
        "ticker": normalized["ticker"],
        "provider": "google_news_rss",
        "count": len(results),
        "results": results,
    }


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
            asyncio.to_thread(_yf_get_quote, ticker),
            ticker=ticker,
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
        allowed_periods = {
            "1d",
            "5d",
            "1mo",
            "3mo",
            "6mo",
            "1y",
            "2y",
            "5y",
            "ytd",
            "max",
        }
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
            asyncio.to_thread(_yf_get_financials, ticker),
            ticker=ticker,
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
            asyncio.to_thread(_yf_get_earnings, ticker),
            ticker=ticker,
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
            asyncio.to_thread(_yf_get_key_ratios, ticker),
            ticker=ticker,
        )
        _cache_set(f"ratios:{ticker}", result, _RATIOS_TTL)
        return result

    async def get_market_news(self, query: str, limit: int = 10) -> Dict[str, Any]:
        from .financial_guardrails import check_rate_limit, with_timeout

        raw_query = query.strip()
        if not raw_query:
            raise ValueError("query is required")

        limit = max(1, min(int(limit), 10))
        ticker = _extract_market_ticker(raw_query)
        normalized_query = ticker or raw_query
        cache_key = f"news:{normalized_query.lower()}:{limit}"
        cached = _cache_get(cache_key)
        if cached:
            cached["_cached"] = True
            return cached

        check_rate_limit()
        result = await with_timeout(
            asyncio.to_thread(_fetch_market_news, raw_query, limit),
            ticker=ticker or normalized_query,
        )
        _cache_set(cache_key, result, _NEWS_TTL)
        return result


# Module-level singleton
financial_data_service = FinancialDataService()
