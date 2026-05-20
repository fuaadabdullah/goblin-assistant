"""
End-to-end integration tests — Phase 5.3.

Tests the complete flow: tool registry → executor → visualization extraction,
simulating what happens when the LLM invokes a tool during chat.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MOCK_FINANCIALS = {
    "ticker": "AAPL",
    "free_cash_flow": 100_000_000_000,
    "shares_outstanding": 15_000_000_000,
    "total_debt": 100_000_000_000,
    "total_cash": 50_000_000_000,
}

_MOCK_QUOTE = {
    "ticker": "AAPL",
    "name": "Apple Inc.",
    "price": 190.0,
    "market_cap": 3_000_000_000_000,
}

_MOCK_RATIOS = {
    "ticker": "AAPL",
    "beta": 1.2,
    "pe_trailing": 30.0,
    "pe_forward": 28.0,
    "revenue_growth": 0.08,
    "dividend_yield": 0.005,
    "debt_to_equity": 150.0,
    "roe": 1.5,
}

_MOCK_EARNINGS = {
    "ticker": "AAPL",
    "trailing_eps": 6.50,
    "forward_eps": 7.00,
    "peg_ratio": 2.5,
    "earnings_quarterly_growth": 0.12,
    "revenue_growth": 0.08,
    "earnings_dates": [
        {
            "date": "2024-10-31",
            "eps_estimate": 1.50,
            "eps_actual": 1.60,
            "surprise_percent": 6.67,
        },
        {
            "date": "2024-07-31",
            "eps_estimate": 1.40,
            "eps_actual": 1.35,
            "surprise_percent": -3.57,
        },
    ],
}

_MOCK_HISTORY = {
    "ticker": "AAPL",
    "period": "1y",
    "interval": "1d",
    "data_points": 3,
    "data": [
        {"date": "2024-01-02", "close": 180.0, "open": 179.0, "high": 181.0, "low": 178.0, "volume": 1000000},
        {"date": "2024-01-03", "close": 182.0, "open": 180.0, "high": 183.0, "low": 179.0, "volume": 1100000},
        {"date": "2024-01-04", "close": 185.0, "open": 182.0, "high": 186.0, "low": 181.0, "volume": 900000},
    ],
}


def _mock_financial_data_service():
    """Create a mock FinancialDataService with all methods."""
    mock = AsyncMock()
    mock.get_financials.return_value = _MOCK_FINANCIALS
    mock.get_current_quote.return_value = _MOCK_QUOTE
    mock.get_key_ratios.return_value = _MOCK_RATIOS
    mock.get_earnings.return_value = _MOCK_EARNINGS
    mock.get_price_history.return_value = _MOCK_HISTORY
    return mock


# ---------------------------------------------------------------------------
# Full skill → visualization pipeline
# ---------------------------------------------------------------------------


class TestDCFEndToEnd:
    """DCF call → result → visualization blocks."""

    @pytest.mark.asyncio
    async def test_dcf_produces_visualizations(self):
        with patch(
            "api.tools.skills.dcf_calculator.financial_data_service",
            _mock_financial_data_service(),
        ):
            from api.tools.skills.dcf_calculator import _handle_dcf_calculator
            from api.services.visualization_service import extract_visualizations

            result = await _handle_dcf_calculator(ticker="AAPL")
            assert "error" not in result
            assert "valuation" in result
            assert "projections" in result

            viz = extract_visualizations("dcf_calculator", {"ticker": "AAPL"}, result)
            assert len(viz) >= 2  # bar chart + sensitivity table + valuation table

            types = [v["type"] for v in viz]
            assert "bar_chart" in types
            assert "table" in types


class TestEarningsEndToEnd:
    """Earnings call → result → visualization blocks."""

    @pytest.mark.asyncio
    async def test_earnings_produces_visualizations(self):
        with patch(
            "api.tools.skills.earnings_summarizer.financial_data_service",
            _mock_financial_data_service(),
        ):
            from api.tools.skills.earnings_summarizer import _handle_earnings_summarizer
            from api.services.visualization_service import extract_visualizations

            result = await _handle_earnings_summarizer(ticker="AAPL")
            assert "error" not in result
            assert "quarters" in result

            viz = extract_visualizations("earnings_summarizer", {"ticker": "AAPL"}, result)
            assert len(viz) >= 1
            types = [v["type"] for v in viz]
            assert "bar_chart" in types or "table" in types


class TestScreenerEndToEnd:
    """Screener call → result → visualization blocks."""

    @pytest.mark.asyncio
    async def test_screener_produces_visualizations(self):
        mock_svc = _mock_financial_data_service()
        with patch(
            "api.tools.skills.stock_screener.financial_data_service",
            mock_svc,
        ):
            from api.tools.skills.stock_screener import _handle_stock_screener
            from api.services.visualization_service import extract_visualizations

            result = await _handle_stock_screener(tickers=["AAPL", "MSFT"], limit=5)
            assert "error" not in result

            viz = extract_visualizations("stock_screener", {}, result)
            # Should get at least a table
            types = [v["type"] for v in viz]
            assert "table" in types


# ---------------------------------------------------------------------------
# Tool loop integration
# ---------------------------------------------------------------------------


class TestToolLoopEndToEnd:
    """Simulate the tool loop with LLM → tool_calls → results → viz."""

    @pytest.mark.asyncio
    async def test_tool_loop_returns_visualizations(self):
        """When the LLM invokes dcf_calculator, the response includes viz."""

        # Mock the financial data service
        mock_svc = _mock_financial_data_service()

        # The first invoke returns tool_calls, second returns text
        call_count = 0

        async def mock_invoke(**kwargs):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # LLM decides to call dcf_calculator
                return {
                    "ok": True,
                    "result": {
                        "raw": {
                            "choices": [{
                                "finish_reason": "tool_calls",
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [{
                                        "id": "call_123",
                                        "type": "function",
                                        "function": {
                                            "name": "dcf_calculator",
                                            "arguments": json.dumps({"ticker": "AAPL"}),
                                        },
                                    }],
                                },
                            }],
                        },
                    },
                }
            else:
                # LLM returns final text response
                return {
                    "ok": True,
                    "result": {
                        "text": "AAPL is valued at $X per share.",
                        "raw": {
                            "choices": [{
                                "finish_reason": "stop",
                                "message": {
                                    "role": "assistant",
                                    "content": "AAPL is valued at $X per share.",
                                },
                            }],
                        },
                    },
                }

        with patch(
            "api.tools.skills.dcf_calculator.financial_data_service",
            mock_svc,
        ):
            from api.tools.executor import run_tool_loop

            messages = [{"role": "user", "content": "Value AAPL for me"}]
            response = await run_tool_loop(
                messages=messages,
                invoke_fn=mock_invoke,
                tools=[{"type": "function", "function": {"name": "dcf_calculator"}}],
            )

            assert response["ok"] is True
            assert "visualizations" in response
            viz = response["visualizations"]
            assert len(viz) >= 2  # bar chart + sensitivity table + valuation table
            types = [v["type"] for v in viz]
            assert "bar_chart" in types

    @pytest.mark.asyncio
    async def test_tool_loop_guardrail_error_handled(self):
        """When a tool raises a rate limit error, it's caught gracefully."""

        async def mock_invoke(**kwargs):
            return {
                "ok": True,
                "result": {
                    "raw": {
                        "choices": [{
                            "finish_reason": "tool_calls",
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [{
                                    "id": "call_456",
                                    "type": "function",
                                    "function": {
                                        "name": "dcf_calculator",
                                        "arguments": json.dumps({"ticker": "AAPL"}),
                                    },
                                }],
                            },
                        }],
                    },
                },
            }

        # Second call returns text
        invoke_count = 0
        original_invoke = mock_invoke

        async def counting_invoke(**kwargs):
            nonlocal invoke_count
            invoke_count += 1
            if invoke_count == 1:
                return await original_invoke(**kwargs)
            return {
                "ok": True,
                "result": {
                    "text": "Rate limit hit, try again.",
                    "raw": {
                        "choices": [{
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": "Rate limit hit, try again.",
                            },
                        }],
                    },
                },
            }

        from api.services.financial_guardrails import RateLimitError

        with patch(
            "api.tools.skills.dcf_calculator.financial_data_service",
        ) as mock_svc:
            mock_svc.get_financials = AsyncMock(side_effect=RateLimitError("rate limit"))

            from api.tools.executor import run_tool_loop

            messages = [{"role": "user", "content": "Value AAPL"}]
            response = await run_tool_loop(
                messages=messages,
                invoke_fn=counting_invoke,
                tools=[{"type": "function", "function": {"name": "dcf_calculator"}}],
            )

            assert response["ok"] is True
            # The tool result message should contain an error dict
            tool_msgs = [m for m in messages if m.get("role") == "tool"]
            assert len(tool_msgs) == 1
            tool_result = json.loads(tool_msgs[0]["content"])
            assert "error" in tool_result
            assert "rate limit" in tool_result["error"]


# ---------------------------------------------------------------------------
# Visualization ↔ Frontend contract tests
# ---------------------------------------------------------------------------


class TestVisualizationFrontendContract:
    """Verify that visualization blocks match the TypeScript type contract."""

    @pytest.mark.asyncio
    async def test_bar_chart_block_shape(self):
        with patch(
            "api.tools.skills.dcf_calculator.financial_data_service",
            _mock_financial_data_service(),
        ):
            from api.tools.skills.dcf_calculator import _handle_dcf_calculator
            from api.services.visualization_service import extract_visualizations

            result = await _handle_dcf_calculator(ticker="AAPL")
            viz = extract_visualizations("dcf_calculator", {"ticker": "AAPL"}, result)

            bar_charts = [v for v in viz if v["type"] == "bar_chart"]
            assert bar_charts
            bc = bar_charts[0]
            # Must have: type, title, data, config
            assert "type" in bc
            assert "title" in bc
            assert "data" in bc
            assert isinstance(bc["data"], list)
            assert "config" in bc
            # config must have xKey and bars
            assert "xKey" in bc["config"]
            assert "bars" in bc["config"]
            for bar in bc["config"]["bars"]:
                assert "dataKey" in bar
                assert "label" in bar

    @pytest.mark.asyncio
    async def test_table_block_shape(self):
        with patch(
            "api.tools.skills.dcf_calculator.financial_data_service",
            _mock_financial_data_service(),
        ):
            from api.tools.skills.dcf_calculator import _handle_dcf_calculator
            from api.services.visualization_service import extract_visualizations

            result = await _handle_dcf_calculator(ticker="AAPL")
            viz = extract_visualizations("dcf_calculator", {"ticker": "AAPL"}, result)

            tables = [v for v in viz if v["type"] == "table"]
            assert tables
            t = tables[0]
            assert "type" in t
            assert "title" in t
            assert "data" in t
            assert isinstance(t["data"], list)
            assert "config" in t
            assert "columns" in t["config"]
            for col in t["config"]["columns"]:
                assert "key" in col
                assert "label" in col
