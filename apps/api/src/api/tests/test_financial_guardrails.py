"""
Tests for financial guardrails — Phase 5.1.

Covers rate limiting, timeout handling, the safe_skill decorator,
and custom exception types used by the financial tool system.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest

from api.services.financial_guardrails import (
    FinancialDataError,
    FetchTimeoutError,
    RateLimitError,
    TickerNotFoundError,
    DataUnavailableError,
    _TokenBucket,
    check_rate_limit,
    safe_skill,
    with_timeout,
)


# ---------------------------------------------------------------------------
# TokenBucket
# ---------------------------------------------------------------------------


class TestTokenBucket:
    def test_acquire_within_capacity(self):
        bucket = _TokenBucket(capacity=5, refill_rate=1.0)
        for _ in range(5):
            assert bucket.try_acquire() is True
        # 6th should fail
        assert bucket.try_acquire() is False

    def test_refill_over_time(self):
        bucket = _TokenBucket(capacity=2, refill_rate=100.0)  # 100/s
        bucket.try_acquire()
        bucket.try_acquire()
        assert bucket.try_acquire() is False
        # Fast-forward by manipulating _last_refill
        bucket._last_refill -= 1.0  # pretend 1s passed
        assert bucket.try_acquire() is True

    def test_does_not_exceed_capacity(self):
        bucket = _TokenBucket(capacity=3, refill_rate=100.0)
        bucket._last_refill -= 100.0  # pretend 100s passed
        # Should cap at capacity
        for _ in range(3):
            assert bucket.try_acquire() is True
        assert bucket.try_acquire() is False


# ---------------------------------------------------------------------------
# check_rate_limit
# ---------------------------------------------------------------------------


class TestCheckRateLimit:
    def test_raises_on_exhaustion(self):
        """Rate limit error raised when bucket is exhausted."""
        with patch("api.services.financial_guardrails._yfinance_bucket") as mock_bucket:
            mock_bucket.try_acquire.return_value = False
            with pytest.raises(RateLimitError, match="rate limit"):
                check_rate_limit()

    def test_passes_when_available(self):
        with patch("api.services.financial_guardrails._yfinance_bucket") as mock_bucket:
            mock_bucket.try_acquire.return_value = True
            check_rate_limit()  # should not raise


# ---------------------------------------------------------------------------
# with_timeout
# ---------------------------------------------------------------------------


class TestWithTimeout:
    @pytest.mark.asyncio
    async def test_returns_result_on_success(self):
        async def quick():
            return 42

        result = await with_timeout(quick(), timeout_s=5.0)
        assert result == 42

    @pytest.mark.asyncio
    async def test_raises_on_timeout(self):
        async def slow():
            await asyncio.sleep(10)

        with pytest.raises(FetchTimeoutError, match="timed out"):
            await with_timeout(slow(), timeout_s=0.05, ticker="AAPL")

    @pytest.mark.asyncio
    async def test_timeout_includes_ticker(self):
        async def slow():
            await asyncio.sleep(10)

        try:
            await with_timeout(slow(), timeout_s=0.05, ticker="MSFT")
        except FetchTimeoutError as e:
            assert e.ticker == "MSFT"
            assert "MSFT" in str(e)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class TestExceptions:
    def test_financial_data_error_to_dict(self):
        e = FinancialDataError("Something broke", ticker="AAPL")
        d = e.to_dict()
        assert d["error"] == "Something broke"
        assert d["ticker"] == "AAPL"

    def test_to_dict_without_ticker(self):
        e = FinancialDataError("General failure")
        d = e.to_dict()
        assert "ticker" not in d

    def test_subclasses(self):
        assert issubclass(TickerNotFoundError, FinancialDataError)
        assert issubclass(DataUnavailableError, FinancialDataError)
        assert issubclass(RateLimitError, FinancialDataError)
        assert issubclass(FetchTimeoutError, FinancialDataError)


# ---------------------------------------------------------------------------
# safe_skill decorator
# ---------------------------------------------------------------------------


class TestSafeSkill:
    @pytest.mark.asyncio
    async def test_passes_through_normal_result(self):
        @safe_skill
        async def my_skill(ticker: str) -> Dict[str, Any]:
            return {"ticker": ticker, "value": 100}

        result = await my_skill(ticker="AAPL")
        assert result == {"ticker": "AAPL", "value": 100}

    @pytest.mark.asyncio
    async def test_catches_financial_data_error(self):
        @safe_skill
        async def failing_skill(ticker: str) -> Dict[str, Any]:
            raise TickerNotFoundError(f"{ticker} not found", ticker=ticker)

        result = await failing_skill(ticker="FAKE")
        assert "error" in result
        assert "FAKE" in result["error"]
        assert result["ticker"] == "FAKE"

    @pytest.mark.asyncio
    async def test_catches_value_error(self):
        @safe_skill
        async def bad_ticker(ticker: str) -> Dict[str, Any]:
            raise ValueError(f"Invalid ticker symbol: {ticker!r}")

        result = await bad_ticker(ticker="!!!")
        assert "error" in result
        assert "Invalid ticker" in result["error"]

    @pytest.mark.asyncio
    async def test_catches_rate_limit_error(self):
        @safe_skill
        async def limited_skill() -> Dict[str, Any]:
            raise RateLimitError("rate limit reached")

        result = await limited_skill()
        assert "error" in result
        assert "rate limit" in result["error"]

    @pytest.mark.asyncio
    async def test_catches_timeout_error(self):
        @safe_skill
        async def slow_skill(ticker: str) -> Dict[str, Any]:
            raise FetchTimeoutError("timed out", ticker=ticker)

        result = await slow_skill(ticker="AAPL")
        assert "error" in result
        assert "timed out" in result["error"]

    @pytest.mark.asyncio
    async def test_unexpected_errors_propagate(self):
        """Non-financial errors should NOT be swallowed."""

        @safe_skill
        async def buggy_skill() -> Dict[str, Any]:
            raise RuntimeError("unexpected bug")

        with pytest.raises(RuntimeError, match="unexpected bug"):
            await buggy_skill()


# ---------------------------------------------------------------------------
# Integration: data service with guardrails
# ---------------------------------------------------------------------------


class TestDataServiceGuardrails:
    """Verify that the data service methods call rate limiting + timeout."""

    @pytest.mark.asyncio
    async def test_get_current_quote_checks_rate_limit(self):
        with patch("api.services.financial_guardrails.check_rate_limit") as mock_rl, \
             patch("api.services.financial_data_service._cache_get", return_value=None), \
             patch("api.services.financial_guardrails.with_timeout", new_callable=AsyncMock) as mock_to:
            mock_to.return_value = {"ticker": "AAPL", "price": 190.0}

            from api.services.financial_data_service import financial_data_service
            result = await financial_data_service.get_current_quote("AAPL")

            mock_rl.assert_called_once()
            mock_to.assert_called_once()
            assert result["ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_cached_quote_skips_rate_limit(self):
        cached_data = {"ticker": "AAPL", "price": 190.0}
        with patch("api.services.financial_guardrails.check_rate_limit") as mock_rl, \
             patch("api.services.financial_data_service._cache_get", return_value=cached_data):
            from api.services.financial_data_service import financial_data_service
            result = await financial_data_service.get_current_quote("AAPL")

            mock_rl.assert_not_called()
            assert result["_cached"] is True

    @pytest.mark.asyncio
    async def test_rate_limit_error_propagates(self):
        with patch("api.services.financial_data_service._cache_get", return_value=None), \
             patch("api.services.financial_guardrails._yfinance_bucket") as mock_bucket:
            mock_bucket.try_acquire.return_value = False

            from api.services.financial_data_service import financial_data_service
            with pytest.raises(RateLimitError):
                await financial_data_service.get_current_quote("AAPL")


# ---------------------------------------------------------------------------
# Integration: executor graceful error conversion
# ---------------------------------------------------------------------------


class TestExecutorGuardrailHandling:
    @pytest.mark.asyncio
    async def test_executor_converts_financial_error(self):
        """execute_tool_call converts FinancialDataError to clean dict."""
        from api.tools.executor import execute_tool_call

        async def handler_that_raises(**kwargs):
            raise RateLimitError("rate limit reached")

        with patch("api.tools.executor.get_tool") as mock_get:
            mock_tool = type("T", (), {
                "handler": staticmethod(handler_that_raises),
            })()
            mock_get.return_value = mock_tool

            result = await execute_tool_call("dcf_calculator", {"ticker": "AAPL"})
            assert "error" in result
            assert "rate limit" in result["error"]
