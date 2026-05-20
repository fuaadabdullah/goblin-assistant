"""
Tests for the financial data service.

Uses the shared yfinance stub from conftest.py to avoid network calls.
"""

from __future__ import annotations

import asyncio
import math
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# yfinance stub is provided by conftest.py (mock_yfinance fixture)

# Now safe to import the service
from api.services.financial_data_service import (
    FinancialDataService,
    _validate_ticker,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    return FinancialDataService()


def _no_cache_get(key):
    return None


def _no_cache_set(key, value, ttl):
    pass


# Patch cache globally so tests don't depend on Redis
@pytest.fixture(autouse=True)
def disable_cache(monkeypatch):
    monkeypatch.setattr(
        "api.services.financial_data_service._cache_get", _no_cache_get
    )
    monkeypatch.setattr(
        "api.services.financial_data_service._cache_set", _no_cache_set
    )


# ---------------------------------------------------------------------------
# Ticker validation
# ---------------------------------------------------------------------------


class TestTickerValidation:
    def test_valid_tickers(self):
        assert _validate_ticker("AAPL") == "AAPL"
        assert _validate_ticker("msft") == "MSFT"
        assert _validate_ticker("BRK.B") == "BRK.B"
        assert _validate_ticker(" tsla ") == "TSLA"

    def test_invalid_tickers(self):
        with pytest.raises(ValueError):
            _validate_ticker("")
        with pytest.raises(ValueError):
            _validate_ticker("TOOLONG")
        with pytest.raises(ValueError):
            _validate_ticker("123")
        with pytest.raises(ValueError):
            _validate_ticker("A-B")
        with pytest.raises(ValueError):
            _validate_ticker("DROP TABLE")


# ---------------------------------------------------------------------------
# Quote
# ---------------------------------------------------------------------------


class TestGetCurrentQuote:
    @pytest.mark.asyncio
    async def test_returns_price_data(self, service):
        result = await service.get_current_quote("AAPL")
        assert result["ticker"] == "AAPL"
        assert result["price"] == 150.0
        assert result["market_cap"] == 2_400_000_000_000
        assert result["currency"] == "USD"
        assert "fetched_at" in result

    @pytest.mark.asyncio
    async def test_rejects_invalid_ticker(self, service):
        with pytest.raises(ValueError):
            await service.get_current_quote("INVALID123")


# ---------------------------------------------------------------------------
# Price history
# ---------------------------------------------------------------------------


class TestGetPriceHistory:
    @pytest.mark.asyncio
    async def test_returns_ohlcv(self, service):
        result = await service.get_price_history("AAPL", "1mo", "1d")
        assert result["ticker"] == "AAPL"
        assert result["period"] == "1mo"
        assert result["interval"] == "1d"
        assert result["data_points"] >= 1
        first = result["data"][0]
        assert "date" in first
        assert "open" in first
        assert "close" in first
        assert "volume" in first

    @pytest.mark.asyncio
    async def test_normalises_invalid_period(self, service):
        result = await service.get_price_history("AAPL", "invalid", "1d")
        assert result["period"] == "1y"  # falls back to default


# ---------------------------------------------------------------------------
# Financials
# ---------------------------------------------------------------------------


class TestGetFinancials:
    @pytest.mark.asyncio
    async def test_returns_financial_data(self, service):
        result = await service.get_financials("AAPL")
        assert result["ticker"] == "AAPL"
        assert result["revenue"] == 400_000_000_000
        assert result["net_income"] == 100_000_000_000
        assert result["free_cash_flow"] == 110_000_000_000
        assert "fetched_at" in result


# ---------------------------------------------------------------------------
# Earnings
# ---------------------------------------------------------------------------


class TestGetEarnings:
    @pytest.mark.asyncio
    async def test_returns_earnings_data(self, service):
        result = await service.get_earnings("AAPL")
        assert result["ticker"] == "AAPL"
        assert result["trailing_eps"] == 6.50
        assert result["forward_eps"] == 7.10
        assert isinstance(result["earnings_dates"], list)


# ---------------------------------------------------------------------------
# Key ratios
# ---------------------------------------------------------------------------


class TestGetKeyRatios:
    @pytest.mark.asyncio
    async def test_returns_ratios(self, service):
        result = await service.get_key_ratios("AAPL")
        assert result["ticker"] == "AAPL"
        assert result["pe_trailing"] == 28.5
        assert result["pe_forward"] == 25.0
        assert result["debt_to_equity"] == 170.0
        assert result["dividend_yield"] == 0.005
        assert result["beta"] == 1.25
