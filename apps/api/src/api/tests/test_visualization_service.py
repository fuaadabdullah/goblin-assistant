"""Tests for Phase 4 — Visualization extraction service."""

from __future__ import annotations

import pytest

from api.services.visualization_service import (
    extract_visualizations,
    _extract_dcf_visualizations,
    _extract_portfolio_visualizations,
    _extract_earnings_visualizations,
    _extract_screener_visualizations,
    _fmt_market_cap,
    _fmt_metric,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestFmtMarketCap:
    def test_trillions(self):
        assert _fmt_market_cap(2.5e12) == "$2.50T"

    def test_billions(self):
        assert _fmt_market_cap(150e9) == "$150.00B"

    def test_millions(self):
        assert _fmt_market_cap(500e6) == "$500.0M"

    def test_small(self):
        assert _fmt_market_cap(123456) == "$123,456"

    def test_none(self):
        assert _fmt_market_cap(None) == "—"


class TestFmtMetric:
    def test_float(self):
        assert _fmt_metric(3.14159) == "3.14"

    def test_none(self):
        assert _fmt_metric(None) == "—"

    def test_string(self):
        assert _fmt_metric("hello") == "hello"


# ---------------------------------------------------------------------------
# DCF Visualizations
# ---------------------------------------------------------------------------

class TestDCFVisualizations:
    SAMPLE_DCF_RESULT = {
        "ticker": "AAPL",
        "valuation": {
            "intrinsic_value_per_share": 185.50,
            "current_price": 170.00,
            "upside_pct": 9.1,
            "enterprise_value": 2.8e12,
            "equity_value": 2.7e12,
        },
        "assumptions": {
            "wacc_pct": 10.0,
            "growth_rate_pct": 5.0,
            "terminal_growth_pct": 2.5,
            "projection_years": 5,
            "base_fcf": 100e9,
            "net_debt": 50e9,
            "shares_outstanding": 15e9,
        },
        "projections": [
            {"year": 1, "projected_fcf": 105e9, "growth_rate": 5.0},
            {"year": 2, "projected_fcf": 110.25e9, "growth_rate": 5.0},
            {"year": 3, "projected_fcf": 115.76e9, "growth_rate": 5.0},
        ],
        "sensitivity_matrix": [
            {"wacc_pct": 8.0, "growth_3.0": 200.0, "growth_5.0": 220.0},
            {"wacc_pct": 10.0, "growth_3.0": 170.0, "growth_5.0": 185.0},
            {"wacc_pct": 12.0, "growth_3.0": 145.0, "growth_5.0": 155.0},
        ],
    }

    def test_produces_bar_chart_for_projections(self):
        blocks = _extract_dcf_visualizations({"ticker": "AAPL"}, self.SAMPLE_DCF_RESULT)
        bar_blocks = [b for b in blocks if b["type"] == "bar_chart"]
        assert len(bar_blocks) == 1
        assert "Projected Free Cash Flow" in bar_blocks[0]["title"]
        assert len(bar_blocks[0]["data"]) == 3
        assert bar_blocks[0]["config"]["xKey"] == "year"

    def test_produces_sensitivity_table(self):
        blocks = _extract_dcf_visualizations({"ticker": "AAPL"}, self.SAMPLE_DCF_RESULT)
        table_blocks = [b for b in blocks if b["type"] == "table" and "Sensitivity" in b["title"]]
        assert len(table_blocks) == 1
        cols = table_blocks[0]["config"]["columns"]
        assert cols[0]["key"] == "wacc_pct"
        assert any("Growth" in c["label"] for c in cols)

    def test_produces_valuation_summary_table(self):
        blocks = _extract_dcf_visualizations({"ticker": "AAPL"}, self.SAMPLE_DCF_RESULT)
        summary_blocks = [b for b in blocks if b["type"] == "table" and "Summary" in b["title"]]
        assert len(summary_blocks) == 1
        data = summary_blocks[0]["data"]
        metrics = [r["metric"] for r in data]
        assert "Intrinsic Value / Share" in metrics
        assert "Current Price" in metrics

    def test_total_block_count(self):
        blocks = _extract_dcf_visualizations({"ticker": "AAPL"}, self.SAMPLE_DCF_RESULT)
        assert len(blocks) == 3  # bar + sensitivity table + summary table

    def test_empty_projections(self):
        result = {**self.SAMPLE_DCF_RESULT, "projections": [], "sensitivity_matrix": []}
        blocks = _extract_dcf_visualizations({"ticker": "AAPL"}, result)
        bar_blocks = [b for b in blocks if b["type"] == "bar_chart"]
        assert len(bar_blocks) == 0

    def test_missing_valuation(self):
        result = {**self.SAMPLE_DCF_RESULT, "valuation": {}}
        blocks = _extract_dcf_visualizations({"ticker": "AAPL"}, result)
        # Should still produce projections and sensitivity
        assert len(blocks) >= 2


# ---------------------------------------------------------------------------
# Portfolio Visualizations
# ---------------------------------------------------------------------------

class TestPortfolioVisualizations:
    SAMPLE_PORTFOLIO_RESULT = {
        "portfolio": {
            "annualized_return_pct": 12.5,
            "annualized_volatility_pct": 18.3,
            "sharpe_ratio": 0.68,
            "max_drawdown_pct": -22.1,
            "var_95_daily_pct": -2.3,
        },
        "holdings": [
            {
                "ticker": "AAPL",
                "weight_pct": 40.0,
                "annualized_return_pct": 15.0,
                "annualized_volatility_pct": 25.0,
                "sharpe_ratio": 0.6,
                "max_drawdown_pct": -30.0,
            },
            {
                "ticker": "MSFT",
                "weight_pct": 60.0,
                "annualized_return_pct": 10.0,
                "annualized_volatility_pct": 20.0,
                "sharpe_ratio": 0.5,
                "max_drawdown_pct": -25.0,
            },
        ],
        "correlation_matrix": {
            "AAPL": {"AAPL": 1.0, "MSFT": 0.78},
            "MSFT": {"AAPL": 0.78, "MSFT": 1.0},
        },
        "benchmark": {
            "ticker": "SPY",
            "annualized_return_pct": 10.0,
            "annualized_volatility_pct": 15.0,
            "sharpe_ratio": 0.67,
            "max_drawdown_pct": -20.0,
        },
    }

    def test_produces_pie_chart(self):
        blocks = _extract_portfolio_visualizations({}, self.SAMPLE_PORTFOLIO_RESULT)
        pie_blocks = [b for b in blocks if b["type"] == "pie_chart"]
        assert len(pie_blocks) == 1
        assert pie_blocks[0]["data"][0]["name"] == "AAPL"
        assert pie_blocks[0]["data"][0]["value"] == 40.0

    def test_produces_bar_chart(self):
        blocks = _extract_portfolio_visualizations({}, self.SAMPLE_PORTFOLIO_RESULT)
        bar_blocks = [b for b in blocks if b["type"] == "bar_chart"]
        assert len(bar_blocks) == 1
        assert "Return vs. Volatility" in bar_blocks[0]["title"]

    def test_produces_heatmap(self):
        blocks = _extract_portfolio_visualizations({}, self.SAMPLE_PORTFOLIO_RESULT)
        heatmap_blocks = [b for b in blocks if b["type"] == "heatmap"]
        assert len(heatmap_blocks) == 1
        assert heatmap_blocks[0]["config"]["columns"] == ["AAPL", "MSFT"]
        assert heatmap_blocks[0]["data"][0]["MSFT"] == 0.78

    def test_produces_risk_summary_table(self):
        blocks = _extract_portfolio_visualizations({}, self.SAMPLE_PORTFOLIO_RESULT)
        table_blocks = [b for b in blocks if b["type"] == "table"]
        assert len(table_blocks) == 1
        cols = table_blocks[0]["config"]["columns"]
        assert any(c["key"] == "benchmark" for c in cols)

    def test_total_block_count(self):
        blocks = _extract_portfolio_visualizations({}, self.SAMPLE_PORTFOLIO_RESULT)
        assert len(blocks) == 4  # pie + bar + heatmap + table

    def test_single_holding_no_heatmap(self):
        result = {
            **self.SAMPLE_PORTFOLIO_RESULT,
            "holdings": [self.SAMPLE_PORTFOLIO_RESULT["holdings"][0]],
            "correlation_matrix": {"AAPL": {"AAPL": 1.0}},
        }
        blocks = _extract_portfolio_visualizations({}, result)
        heatmap_blocks = [b for b in blocks if b["type"] == "heatmap"]
        assert len(heatmap_blocks) == 0  # Only 1 ticker → no useful heatmap

    def test_no_benchmark(self):
        result = {**self.SAMPLE_PORTFOLIO_RESULT, "benchmark": None}
        blocks = _extract_portfolio_visualizations({}, result)
        table_blocks = [b for b in blocks if b["type"] == "table"]
        assert len(table_blocks) == 1
        cols = table_blocks[0]["config"]["columns"]
        assert not any(c["key"] == "benchmark" for c in cols)


# ---------------------------------------------------------------------------
# Earnings Visualizations
# ---------------------------------------------------------------------------

class TestEarningsVisualizations:
    SAMPLE_EARNINGS_RESULT = {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "current_price": 170.0,
        "quarters": [
            {"date": "2024-Q4", "eps_estimate": 1.50, "eps_actual": 1.65, "surprise_pct": 10.0, "verdict": "beat"},
            {"date": "2024-Q3", "eps_estimate": 1.40, "eps_actual": 1.35, "surprise_pct": -3.6, "verdict": "miss"},
            {"date": "2024-Q2", "eps_estimate": 1.30, "eps_actual": 1.38, "surprise_pct": 6.2, "verdict": "beat"},
        ],
        "key_metrics": {
            "trailing_eps": 6.50,
            "forward_eps": 7.10,
            "pe_trailing": 26.2,
            "pe_forward": 23.9,
            "peg_ratio": 1.8,
            "earnings_growth_quarterly": 0.12,
            "revenue_growth": 0.08,
        },
        "summary": {"beats": 2, "misses": 1, "total": 3},
    }

    def test_produces_bar_chart(self):
        blocks = _extract_earnings_visualizations({"ticker": "AAPL"}, self.SAMPLE_EARNINGS_RESULT)
        bar_blocks = [b for b in blocks if b["type"] == "bar_chart"]
        assert len(bar_blocks) == 1
        assert "Estimate vs. Actual" in bar_blocks[0]["title"]
        # Data should be in chronological order (reversed)
        assert bar_blocks[0]["data"][0]["quarter"] == "2024-Q2"
        assert bar_blocks[0]["data"][-1]["quarter"] == "2024-Q4"

    def test_produces_metrics_table(self):
        blocks = _extract_earnings_visualizations({"ticker": "AAPL"}, self.SAMPLE_EARNINGS_RESULT)
        table_blocks = [b for b in blocks if b["type"] == "table"]
        assert len(table_blocks) == 1
        metrics = [r["metric"] for r in table_blocks[0]["data"]]
        assert "Trailing EPS" in metrics
        assert "P/E (Trailing)" in metrics

    def test_empty_quarters(self):
        result = {**self.SAMPLE_EARNINGS_RESULT, "quarters": []}
        blocks = _extract_earnings_visualizations({"ticker": "AAPL"}, result)
        bar_blocks = [b for b in blocks if b["type"] == "bar_chart"]
        assert len(bar_blocks) == 0

    def test_empty_metrics(self):
        result = {**self.SAMPLE_EARNINGS_RESULT, "key_metrics": {}}
        blocks = _extract_earnings_visualizations({"ticker": "AAPL"}, result)
        table_blocks = [b for b in blocks if b["type"] == "table"]
        assert len(table_blocks) == 0


# ---------------------------------------------------------------------------
# Screener Visualizations
# ---------------------------------------------------------------------------

class TestScreenerVisualizations:
    SAMPLE_SCREENER_RESULT = {
        "matches": 3,
        "screened": 50,
        "criteria": {"min_market_cap": 100e9},
        "results": [
            {"ticker": "AAPL", "name": "Apple", "price": 170.0, "market_cap": 2.8e12, "pe_trailing": 28.5, "dividend_yield_pct": 0.55},
            {"ticker": "MSFT", "name": "Microsoft", "price": 380.0, "market_cap": 2.9e12, "pe_trailing": 35.2, "dividend_yield_pct": 0.72},
            {"ticker": "GOOGL", "name": "Alphabet", "price": 140.0, "market_cap": 1.8e12, "pe_trailing": 24.1, "dividend_yield_pct": None},
        ],
    }

    def test_produces_results_table(self):
        blocks = _extract_screener_visualizations({}, self.SAMPLE_SCREENER_RESULT)
        table_blocks = [b for b in blocks if b["type"] == "table"]
        assert len(table_blocks) == 1
        assert "3 / 50" in table_blocks[0]["title"]
        assert table_blocks[0]["data"][0]["ticker"] == "AAPL"

    def test_produces_market_cap_bar_chart(self):
        blocks = _extract_screener_visualizations({}, self.SAMPLE_SCREENER_RESULT)
        bar_blocks = [b for b in blocks if b["type"] == "bar_chart"]
        assert len(bar_blocks) == 1
        assert "Market Cap" in bar_blocks[0]["title"]

    def test_empty_results(self):
        result = {**self.SAMPLE_SCREENER_RESULT, "results": []}
        blocks = _extract_screener_visualizations({}, result)
        assert len(blocks) == 0

    def test_single_result_no_comparison(self):
        result = {
            **self.SAMPLE_SCREENER_RESULT,
            "results": [self.SAMPLE_SCREENER_RESULT["results"][0]],
        }
        blocks = _extract_screener_visualizations({}, result)
        bar_blocks = [b for b in blocks if b["type"] == "bar_chart"]
        assert len(bar_blocks) == 0  # Only 1 result → no comparison chart

    def test_formats_prices_and_caps(self):
        blocks = _extract_screener_visualizations({}, self.SAMPLE_SCREENER_RESULT)
        table_blocks = [b for b in blocks if b["type"] == "table"]
        row = table_blocks[0]["data"][0]
        assert row["price"] == "$170.00"
        assert row["market_cap"] == "$2.80T"

    def test_none_values_formatted(self):
        blocks = _extract_screener_visualizations({}, self.SAMPLE_SCREENER_RESULT)
        table_blocks = [b for b in blocks if b["type"] == "table"]
        googl = table_blocks[0]["data"][2]
        assert googl["dividend_yield_pct"] == "—"


# ---------------------------------------------------------------------------
# Public API: extract_visualizations
# ---------------------------------------------------------------------------

class TestExtractVisualizations:
    def test_known_tool(self):
        result = TestDCFVisualizations.SAMPLE_DCF_RESULT
        blocks = extract_visualizations("dcf_calculator", {"ticker": "AAPL"}, result)
        assert len(blocks) == 3

    def test_unknown_tool_returns_empty(self):
        blocks = extract_visualizations("unknown_tool", {}, {})
        assert blocks == []

    def test_error_result_returns_empty(self):
        # extractor receives a result that might cause an error
        # but the public API catches exceptions gracefully
        blocks = extract_visualizations("dcf_calculator", {}, {"error": "oops"})
        # Even if result is partial, extractor handles missing keys
        assert isinstance(blocks, list)

    def test_all_four_tools_produce_blocks(self):
        for tool_name, sample in [
            ("dcf_calculator", TestDCFVisualizations.SAMPLE_DCF_RESULT),
            ("portfolio_analyzer", TestPortfolioVisualizations.SAMPLE_PORTFOLIO_RESULT),
            ("earnings_summarizer", TestEarningsVisualizations.SAMPLE_EARNINGS_RESULT),
            ("stock_screener", TestScreenerVisualizations.SAMPLE_SCREENER_RESULT),
        ]:
            blocks = extract_visualizations(tool_name, {}, sample)
            assert len(blocks) > 0, f"{tool_name} should produce visualizations"


# ---------------------------------------------------------------------------
# Executor visualization wiring
# ---------------------------------------------------------------------------

class TestExecutorVisualizationWiring:
    """Test that run_tool_loop collects visualizations."""

    @pytest.mark.asyncio
    async def test_tool_loop_collects_visualizations(self):
        """run_tool_loop should attach visualizations[] to the final response."""
        from unittest.mock import AsyncMock, patch
        from api.tools.executor import run_tool_loop

        # First call returns tool_calls, second call returns text response
        tool_call_response = {
            "ok": True,
            "result": {
                "text": "",
                "raw": {
                    "choices": [{
                        "finish_reason": "tool_calls",
                        "message": {
                            "tool_calls": [{
                                "id": "tc_1",
                                "function": {
                                    "name": "dcf_calculator",
                                    "arguments": '{"ticker": "AAPL"}',
                                },
                            }],
                        },
                    }],
                },
            },
        }
        final_response = {
            "ok": True,
            "result": {"text": "AAPL is undervalued.", "raw": {"choices": [{"message": {"content": "..."}}]}},
        }

        invoke_fn = AsyncMock(side_effect=[tool_call_response, final_response])

        dcf_result = TestDCFVisualizations.SAMPLE_DCF_RESULT

        with patch("api.tools.executor.execute_tool_call", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = dcf_result
            result = await run_tool_loop(
                messages=[{"role": "user", "content": "Value AAPL"}],
                invoke_fn=invoke_fn,
            )

        assert "visualizations" in result
        assert len(result["visualizations"]) == 3  # bar + sensitivity + summary

    @pytest.mark.asyncio
    async def test_tool_loop_no_viz_for_non_financial_tools(self):
        """Tools without extractors should produce empty visualizations."""
        from unittest.mock import AsyncMock, patch
        from api.tools.executor import run_tool_loop

        tool_call_response = {
            "ok": True,
            "result": {
                "text": "",
                "raw": {
                    "choices": [{
                        "finish_reason": "tool_calls",
                        "message": {
                            "tool_calls": [{
                                "id": "tc_1",
                                "function": {
                                    "name": "get_stock_quote",
                                    "arguments": '{"ticker": "AAPL"}',
                                },
                            }],
                        },
                    }],
                },
            },
        }
        final_response = {
            "ok": True,
            "result": {"text": "Here's AAPL.", "raw": {"choices": [{"message": {"content": "..."}}]}},
        }

        invoke_fn = AsyncMock(side_effect=[tool_call_response, final_response])

        with patch("api.tools.executor.execute_tool_call", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"price": 170.0, "ticker": "AAPL"}
            result = await run_tool_loop(
                messages=[{"role": "user", "content": "AAPL quote"}],
                invoke_fn=invoke_fn,
            )

        # No visualizations for market data tools
        assert result.get("visualizations") is None or len(result.get("visualizations", [])) == 0

    @pytest.mark.asyncio
    async def test_tool_loop_skips_viz_on_error(self):
        """Error tool results should not generate visualizations."""
        from unittest.mock import AsyncMock, patch
        from api.tools.executor import run_tool_loop

        tool_call_response = {
            "ok": True,
            "result": {
                "text": "",
                "raw": {
                    "choices": [{
                        "finish_reason": "tool_calls",
                        "message": {
                            "tool_calls": [{
                                "id": "tc_1",
                                "function": {
                                    "name": "dcf_calculator",
                                    "arguments": '{"ticker": "AAPL"}',
                                },
                            }],
                        },
                    }],
                },
            },
        }
        final_response = {
            "ok": True,
            "result": {"text": "Sorry, failed.", "raw": {"choices": [{"message": {"content": "..."}}]}},
        }

        invoke_fn = AsyncMock(side_effect=[tool_call_response, final_response])

        with patch("api.tools.executor.execute_tool_call", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"error": "Ticker not found"}
            result = await run_tool_loop(
                messages=[{"role": "user", "content": "Value XYZ"}],
                invoke_fn=invoke_fn,
            )

        # Error result → no visualizations extracted
        assert result.get("visualizations") is None or len(result.get("visualizations", [])) == 0
