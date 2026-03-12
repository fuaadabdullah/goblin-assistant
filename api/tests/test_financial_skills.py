"""
Tests for Phase 2 financial skills: DCF calculator, portfolio analyzer,
earnings summarizer, and stock screener.

Uses the shared yfinance + embedding stubs from conftest.py.
All tests are fully mocked — no network calls.
"""

from __future__ import annotations

import sys

import pytest

# Stubs are provided by conftest.py (mock_embedding_service, mock_yfinance)

from api.tools.registry import TOOL_REGISTRY
from api.tools.skills.dcf_calculator import (
    _project_fcf,
    _discount_fcf,
    _terminal_value,
    _handle_dcf_calculator,
)
from api.tools.skills.portfolio_analyzer import (
    _daily_returns,
    _annualized_return,
    _annualized_volatility,
    _sharpe_ratio,
    _max_drawdown,
    _var_95,
    _correlation,
    _handle_portfolio_analyzer,
)
from api.tools.skills.earnings_summarizer import _handle_earnings_summarizer
from api.tools.skills.stock_screener import _handle_stock_screener


# Disable Redis caching and rate limiting for all tests
@pytest.fixture(autouse=True)
def _no_redis(monkeypatch):
    import api.services.financial_data_service as fds
    monkeypatch.setattr(fds, "_cache_get", lambda key: None)
    monkeypatch.setattr(fds, "_cache_set", lambda key, value, ttl: None)

    import api.services.financial_guardrails as fg
    monkeypatch.setattr(fg, "check_rate_limit", lambda: None)


# ===================================================================
# DCF Calculator
# ===================================================================


class TestDCFHelpers:
    def test_project_fcf(self):
        proj = _project_fcf(100.0, 0.10, 3)
        assert len(proj) == 3
        assert proj[0]["year"] == 1
        assert proj[0]["projected_fcf"] == pytest.approx(110.0, rel=0.01)
        assert proj[2]["projected_fcf"] == pytest.approx(133.1, rel=0.01)

    def test_discount_fcf(self):
        proj = [
            {"year": 1, "projected_fcf": 110.0},
            {"year": 2, "projected_fcf": 121.0},
        ]
        pv = _discount_fcf(proj, 0.10)
        expected = 110 / 1.10 + 121 / 1.10**2
        assert pv == pytest.approx(expected, rel=0.01)

    def test_terminal_value(self):
        tv = _terminal_value(100.0, 0.025, 0.10)
        # TV = 100 * 1.025 / (0.10 - 0.025) = 102.5 / 0.075 = 1366.67
        assert tv == pytest.approx(1366.67, rel=0.01)

    def test_terminal_value_wacc_equals_growth(self):
        assert _terminal_value(100.0, 0.10, 0.10) == 0.0


class TestDCFCalculator:
    @pytest.mark.asyncio
    async def test_full_dcf_returns_valuation(self):
        result = await _handle_dcf_calculator("AAPL")

        assert "valuation" in result
        assert "assumptions" in result
        assert "projections" in result
        assert "sensitivity_matrix" in result

        val = result["valuation"]
        assert val["current_price"] == 150.0
        assert isinstance(val["intrinsic_value_per_share"], float)
        assert isinstance(val["upside_pct"], float)
        assert val["enterprise_value"] > 0

    @pytest.mark.asyncio
    async def test_dcf_custom_assumptions(self):
        result = await _handle_dcf_calculator(
            "MSFT", wacc=0.09, growth_rate=0.10, projection_years=10
        )
        assert len(result["projections"]) == 10
        assert result["assumptions"]["wacc_pct"] == pytest.approx(9.0, rel=0.01)
        assert result["assumptions"]["growth_rate_pct"] == pytest.approx(10.0, rel=0.01)

    @pytest.mark.asyncio
    async def test_dcf_negative_fcf_returns_error(self):
        """Tickers with negative FCF should return a clear error."""
        import api.services.financial_data_service as fds

        original = fds._yf_get_financials

        def _neg_fcf(ticker):
            data = original(ticker)
            data["free_cash_flow"] = -5_000_000
            return data

        fds._yf_get_financials = _neg_fcf
        try:
            result = await _handle_dcf_calculator("AAPL")
            assert "error" in result
        finally:
            fds._yf_get_financials = original

    @pytest.mark.asyncio
    async def test_dcf_registered(self):
        assert "dcf_calculator" in TOOL_REGISTRY


# ===================================================================
# Portfolio Analyzer
# ===================================================================


class TestPortfolioHelpers:
    def test_daily_returns(self):
        rets = _daily_returns([100, 110, 105])
        assert len(rets) == 2
        assert rets[0] == pytest.approx(0.10, rel=0.01)
        assert rets[1] == pytest.approx(-0.04545, rel=0.01)

    def test_annualized_return(self):
        # 1% daily for 252 days
        daily = [0.01] * 252
        ann = _annualized_return(daily)
        assert ann > 1.0  # Should be a very high annualized number

    def test_annualized_volatility(self):
        daily = [0.01, -0.01, 0.01, -0.01] * 63  # 252 days
        vol = _annualized_volatility(daily)
        assert vol > 0

    def test_sharpe_ratio(self):
        assert _sharpe_ratio(0.12, 0.15, 0.04) == pytest.approx((0.12 - 0.04) / 0.15, rel=0.01)
        assert _sharpe_ratio(0.10, 0.0) is None

    def test_max_drawdown(self):
        prices = [100, 110, 90, 95, 80, 100]
        dd = _max_drawdown(prices)
        # Peak was 110, trough was 80 → dd = 30/110 ≈ 0.2727
        assert dd == pytest.approx(30 / 110, rel=0.01)

    def test_var_95(self):
        import random
        random.seed(42)
        rets = [random.gauss(0, 0.02) for _ in range(252)]
        var = _var_95(rets)
        assert var < 0  # 5th percentile should be negative

    def test_correlation_perfect(self):
        a = [0.01, -0.02, 0.03, 0.01, -0.01]
        assert _correlation(a, a) == pytest.approx(1.0, rel=0.01)

    def test_correlation_opposite(self):
        a = [0.01, -0.02, 0.03, 0.01, -0.01]
        b = [-x for x in a]
        assert _correlation(a, b) == pytest.approx(-1.0, rel=0.01)


class TestPortfolioAnalyzer:
    @pytest.mark.asyncio
    async def test_full_analysis(self):
        result = await _handle_portfolio_analyzer(
            holdings=[
                {"ticker": "AAPL", "shares": 10},
                {"ticker": "MSFT", "shares": 5},
            ],
        )

        assert "portfolio" in result
        assert "holdings" in result
        assert "correlation_matrix" in result
        assert "benchmark" in result

        port = result["portfolio"]
        assert "annualized_return_pct" in port
        assert "sharpe_ratio" in port
        assert "max_drawdown_pct" in port
        assert "var_95_daily_pct" in port

        assert len(result["holdings"]) == 2
        assert "AAPL" in result["correlation_matrix"]

    @pytest.mark.asyncio
    async def test_empty_holdings_error(self):
        result = await _handle_portfolio_analyzer(holdings=[])
        assert "error" in result

    @pytest.mark.asyncio
    async def test_weight_normalization(self):
        result = await _handle_portfolio_analyzer(
            holdings=[
                {"ticker": "AAPL", "weight": 60},
                {"ticker": "MSFT", "weight": 40},
            ],
        )
        weights = {h["ticker"]: h["weight_pct"] for h in result["holdings"]}
        assert weights["AAPL"] == pytest.approx(60.0, rel=0.01)
        assert weights["MSFT"] == pytest.approx(40.0, rel=0.01)

    @pytest.mark.asyncio
    async def test_registered(self):
        assert "portfolio_analyzer" in TOOL_REGISTRY


# ===================================================================
# Earnings Summarizer
# ===================================================================


class TestEarningsSummarizer:
    @pytest.mark.asyncio
    async def test_basic_summary(self):
        result = await _handle_earnings_summarizer("AAPL")

        assert result["ticker"] == "AAPL"
        assert "company_name" in result
        assert "current_price" in result
        assert "summary" in result
        assert "key_metrics" in result
        assert "trailing_eps" in result["key_metrics"]

    @pytest.mark.asyncio
    async def test_with_earnings_dates(self):
        """Inject fake earnings_dates to test verdict logic."""
        import pandas as pd

        # Patch the Ticker to return real earnings_dates
        _yf_mod = sys.modules["yfinance"]
        original_class = _yf_mod.Ticker

        class _PatchedTicker(original_class):
            def __init__(self, ticker):
                super().__init__(ticker)
                dates = pd.date_range("2025-01-01", periods=4, freq="QS")
                self.earnings_dates = pd.DataFrame({
                    "EPS Estimate": [1.50, 1.40, 1.30, 1.20],
                    "Reported EPS": [1.60, 1.35, 1.45, 1.25],
                    "Surprise(%)": [6.67, -3.57, 11.54, 4.17],
                }, index=dates)

        _yf_mod.Ticker = _PatchedTicker
        try:
            result = await _handle_earnings_summarizer("AAPL", num_quarters=4)

            quarters = result["quarters"]
            assert len(quarters) == 4
            assert quarters[0]["verdict"] == "beat"
            assert quarters[1]["verdict"] == "miss"

            summary = result["summary"]
            assert summary["beats"] >= 1
            assert summary["total"] == 4
        finally:
            _yf_mod.Ticker = original_class

    @pytest.mark.asyncio
    async def test_registered(self):
        assert "earnings_summarizer" in TOOL_REGISTRY


# ===================================================================
# Stock Screener
# ===================================================================


class TestStockScreener:
    @pytest.mark.asyncio
    async def test_basic_screen_custom_tickers(self):
        result = await _handle_stock_screener(
            tickers=["AAPL", "MSFT"],
        )
        assert result["screened"] == 2
        assert result["matches"] >= 1
        assert len(result["results"]) >= 1

    @pytest.mark.asyncio
    async def test_pe_filter(self):
        result = await _handle_stock_screener(
            tickers=["AAPL", "MSFT"],
            max_pe=30.0,
        )
        # AAPL PE=28.5 passes, MSFT PE=35 fails
        tickers_found = [r["ticker"] for r in result["results"]]
        assert "AAPL" in tickers_found
        assert "MSFT" not in tickers_found

    @pytest.mark.asyncio
    async def test_market_cap_filter(self):
        result = await _handle_stock_screener(
            tickers=["AAPL", "MSFT"],
            min_market_cap=2_500_000_000_000,  # 2.5T
        )
        tickers_found = [r["ticker"] for r in result["results"]]
        # MSFT mcap=2.8T passes, AAPL mcap=2.4T fails
        assert "MSFT" in tickers_found
        assert "AAPL" not in tickers_found

    @pytest.mark.asyncio
    async def test_dividend_yield_filter(self):
        result = await _handle_stock_screener(
            tickers=["AAPL", "MSFT"],
            min_dividend_yield=0.006,
        )
        tickers_found = [r["ticker"] for r in result["results"]]
        # AAPL yield=0.005 fails, MSFT yield=0.008 passes
        assert "MSFT" in tickers_found
        assert "AAPL" not in tickers_found

    @pytest.mark.asyncio
    async def test_no_matches(self):
        result = await _handle_stock_screener(
            tickers=["AAPL"],
            max_pe=5.0,  # unreasonably low
        )
        assert result["matches"] == 0
        assert len(result["results"]) == 0

    @pytest.mark.asyncio
    async def test_limit_respected(self):
        result = await _handle_stock_screener(
            tickers=["AAPL", "MSFT"],
            limit=1,
        )
        assert len(result["results"]) <= 1

    @pytest.mark.asyncio
    async def test_registered(self):
        assert "stock_screener" in TOOL_REGISTRY


# ===================================================================
# Registration sanity check
# ===================================================================


class TestAllSkillsRegistered:
    def test_all_phase2_skills_in_registry(self):
        expected = {
            "dcf_calculator",
            "portfolio_analyzer",
            "earnings_summarizer",
            "stock_screener",
        }
        assert expected.issubset(set(TOOL_REGISTRY.keys()))

    def test_all_have_openai_schemas(self):
        for name in ["dcf_calculator", "portfolio_analyzer", "earnings_summarizer", "stock_screener"]:
            tool = TOOL_REGISTRY[name]
            schema = tool.to_openai_schema()
            assert schema["type"] == "function"
            assert schema["function"]["name"] == name
            assert "parameters" in schema["function"]
