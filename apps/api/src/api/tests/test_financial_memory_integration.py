"""
Tests for Phase 3 — Financial Memory Integration.

Covers:
  • tool_result_memory_service: extraction helpers + extract_and_promote
  • retrieval_service: financial profile injection into context bundle
  • executor: memory promotion wiring (user_id / conversation_id passthrough)

All IO (DB, embeddings, retrieval) is mocked — no network or database.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Import units under test ──────────────────────────────────────

from api.services.tool_result_memory_service import (
    _extract_dcf_facts,
    _extract_earnings_facts,
    _extract_portfolio_facts,
    _extract_screener_facts,
    _parse_dcf_assumptions,
    extract_and_promote,
    get_financial_profile,
)

from api.tools.executor import execute_tool_call, run_tool_loop


# ===================================================================
# DCF fact extraction
# ===================================================================


class TestExtractDCFFacts:
    def test_basic_extraction(self):
        result = {
            "ticker": "AAPL",
            "valuation": {
                "intrinsic_value_per_share": 180.50,
                "upside_percent": 20.3,
                "enterprise_value": 3_000_000_000_000,
            },
            "assumptions": {
                "wacc": 0.10,
                "growth_rate": 0.08,
                "projection_years": 5,
                "terminal_growth_rate": 0.025,
            },
        }
        facts = _extract_dcf_facts(result, {"ticker": "AAPL"})
        assert len(facts) == 2
        assert facts[0]["category"] == "instrument"
        assert "$180.50" in facts[0]["content"]
        assert "+20.3%" in facts[0]["content"]
        assert facts[1]["category"] == "financial_profile"
        assert "WACC=10.0%" in facts[1]["content"]
        assert "growth=8.0%" in facts[1]["content"]

    def test_negative_upside(self):
        result = {
            "ticker": "MSFT",
            "valuation": {"intrinsic_value_per_share": 200.0, "upside_percent": -15.0},
            "assumptions": {"wacc": 0.12, "growth_rate": 0.05, "projection_years": 5, "terminal_growth_rate": 0.025},
        }
        facts = _extract_dcf_facts(result, {"ticker": "MSFT"})
        assert "-15.0%" in facts[0]["content"]

    def test_missing_valuation_returns_assumption_only(self):
        result = {
            "ticker": "XYZ",
            "valuation": {},
            "assumptions": {"wacc": 0.09, "growth_rate": 0.06, "projection_years": 7, "terminal_growth_rate": 0.03},
        }
        facts = _extract_dcf_facts(result, {"ticker": "XYZ"})
        assert len(facts) == 1
        assert facts[0]["category"] == "financial_profile"


# ===================================================================
# Portfolio fact extraction
# ===================================================================


class TestExtractPortfolioFacts:
    def test_basic_extraction(self):
        result = {
            "holdings": [
                {"ticker": "AAPL", "weight": 0.5},
                {"ticker": "MSFT", "weight": 0.5},
            ],
            "portfolio_metrics": {
                "annualized_return": 0.12,
                "annualized_volatility": 0.18,
                "sharpe_ratio": 0.67,
                "max_drawdown": -0.10,
            },
        }
        facts = _extract_portfolio_facts(result, {})
        assert len(facts) == 2
        assert facts[0]["category"] == "portfolio_action"
        assert "AAPL" in facts[0]["content"]
        assert "MSFT" in facts[0]["content"]
        assert facts[1]["category"] == "risk_signal"
        assert "return=12.0%" in facts[1]["content"]

    def test_empty_holdings(self):
        result = {"holdings": [], "portfolio_metrics": {}}
        facts = _extract_portfolio_facts(result, {})
        assert len(facts) == 0


# ===================================================================
# Earnings fact extraction
# ===================================================================


class TestExtractEarningsFacts:
    def test_basic_extraction(self):
        result = {
            "ticker": "AAPL",
            "summary": {"beats": 3, "total": 4, "streak": "3 consecutive beats"},
        }
        facts = _extract_earnings_facts(result, {"ticker": "AAPL"})
        assert len(facts) == 1
        assert "3/4 beats" in facts[0]["content"]
        assert "3 consecutive beats" in facts[0]["content"]

    def test_no_streak(self):
        result = {
            "ticker": "MSFT",
            "summary": {"beats": 2, "total": 4, "streak": None},
        }
        facts = _extract_earnings_facts(result, {"ticker": "MSFT"})
        assert len(facts) == 1
        assert "streak" not in facts[0]["content"].lower()

    def test_zero_total_returns_empty(self):
        result = {"ticker": "ZZZ", "summary": {"beats": 0, "total": 0}}
        facts = _extract_earnings_facts(result, {"ticker": "ZZZ"})
        assert len(facts) == 0


# ===================================================================
# Screener fact extraction
# ===================================================================


class TestExtractScreenerFacts:
    def test_basic_extraction(self):
        result = {
            "matches": [
                {"ticker": "AAPL", "market_cap": 2_400e9},
                {"ticker": "MSFT", "market_cap": 2_800e9},
            ],
            "criteria_applied": {"min_market_cap": 1e12},
        }
        facts = _extract_screener_facts(result, {})
        assert len(facts) == 1
        assert "AAPL" in facts[0]["content"]
        assert facts[0]["category"] == "financial_profile"

    def test_empty_matches(self):
        result = {"matches": [], "criteria_applied": {}}
        facts = _extract_screener_facts(result, {})
        assert len(facts) == 0


# ===================================================================
# DCF assumption parsing (round-trip)
# ===================================================================


class TestParseDCFAssumptions:
    def test_round_trip(self):
        text = (
            "DCF assumptions for AAPL: WACC=10.0%, growth=8.0%, "
            "projection_years=5, terminal_growth=2.5%"
        )
        parsed = _parse_dcf_assumptions(text)
        assert parsed["ticker"] == "AAPL"
        assert abs(parsed["wacc"] - 0.10) < 1e-6
        assert abs(parsed["growth_rate"] - 0.08) < 1e-6
        assert parsed["projection_years"] == 5
        assert abs(parsed["terminal_growth"] - 0.025) < 1e-6

    def test_partial_text(self):
        parsed = _parse_dcf_assumptions("WACC=12.0%")
        assert abs(parsed["wacc"] - 0.12) < 1e-6
        assert "ticker" not in parsed


# ===================================================================
# extract_and_promote integration
# ===================================================================


class TestExtractAndPromote:
    @pytest.mark.asyncio
    async def test_promotes_dcf_facts(self):
        result = {
            "ticker": "AAPL",
            "valuation": {"intrinsic_value_per_share": 180.0, "upside_percent": 20.0},
            "assumptions": {"wacc": 0.10, "growth_rate": 0.08, "projection_years": 5, "terminal_growth_rate": 0.025},
        }
        with patch(
            "api.services.tool_result_memory_service.memory_promotion_service"
        ) as mock_promo:
            from api.services.memory_promotion_service import PromotionResult, PromotionGate

            mock_promo.evaluate_promotion_candidate = AsyncMock(
                return_value=PromotionResult(
                    promoted=True,
                    gates_passed=[PromotionGate.CONTENT_QUALITY],
                    gates_failed=[],
                    reason="All gates passed",
                )
            )
            results = await extract_and_promote(
                tool_name="dcf_calculator",
                tool_args={"ticker": "AAPL"},
                tool_result=result,
                user_id="u1",
                conversation_id="c1",
            )
            assert len(results) == 2
            assert all(r.promoted for r in results)
            assert mock_promo.evaluate_promotion_candidate.call_count == 2

    @pytest.mark.asyncio
    async def test_skips_non_financial_tools(self):
        results = await extract_and_promote(
            tool_name="get_current_time",
            tool_args={},
            tool_result={"time": "12:00"},
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_skips_error_results(self):
        results = await extract_and_promote(
            tool_name="dcf_calculator",
            tool_args={"ticker": "AAPL"},
            tool_result={"error": "No FCF data"},
        )
        assert results == []


# ===================================================================
# get_financial_profile
# ===================================================================


class TestGetFinancialProfile:
    @pytest.mark.asyncio
    async def test_assembles_profile(self):
        mock_retrieval = AsyncMock()
        mock_retrieval.retrieve_memory_facts = AsyncMock(return_value=[
            {
                "fact_text": "DCF assumptions for AAPL: WACC=10.0%, growth=8.0%, projection_years=5, terminal_growth=2.5%",
                "category": "financial_profile",
            },
            {
                "fact_text": "Portfolio holdings analyzed: AAPL, MSFT, GOOG",
                "category": "portfolio_action",
            },
            {
                "fact_text": "Portfolio risk snapshot: return=12.0%, volatility=18.0%, Sharpe=0.67, max drawdown=-10.0%",
                "category": "risk_signal",
            },
            {
                "fact_text": "DCF valuation for TSLA: intrinsic value $300.00/share",
                "category": "instrument",
            },
        ])

        profile = await get_financial_profile("u1", retrieval_svc=mock_retrieval)

        assert profile["last_dcf_assumptions"]["ticker"] == "AAPL"
        assert abs(profile["last_dcf_assumptions"]["wacc"] - 0.10) < 1e-6
        assert "AAPL" in profile["portfolio_snapshot"]
        assert "return=12.0%" in profile["risk_snapshot"]
        assert "TSLA" in profile["watched_tickers"]
        assert "DCF" in profile["watched_tickers"]  # regex picks up caps

    @pytest.mark.asyncio
    async def test_empty_facts_returns_empty_profile(self):
        mock_retrieval = AsyncMock()
        mock_retrieval.retrieve_memory_facts = AsyncMock(return_value=[])
        profile = await get_financial_profile("u1", retrieval_svc=mock_retrieval)
        assert profile["watched_tickers"] == []
        assert profile["last_dcf_assumptions"] == {}
        assert profile["portfolio_snapshot"] is None

    @pytest.mark.asyncio
    async def test_retrieval_error_returns_empty_profile(self):
        mock_retrieval = AsyncMock()
        mock_retrieval.retrieve_memory_facts = AsyncMock(side_effect=RuntimeError("DB down"))
        profile = await get_financial_profile("u1", retrieval_svc=mock_retrieval)
        assert profile["watched_tickers"] == []


# ===================================================================
# ContextBuilder financial profile injection
# ===================================================================


class TestContextBuilderFinancialProfile:
    def test_profile_injected_into_prompt(self):
        from api.services.retrieval_service import ContextBuilder

        bundle = {
            "summaries": [],
            "tasks": [],
            "memory_facts": [],
            "messages": [],
            "financial_profile": {
                "watched_tickers": ["AAPL", "MSFT"],
                "last_dcf_assumptions": {"ticker": "AAPL", "wacc": 0.10, "growth_rate": 0.08},
                "portfolio_snapshot": "Holdings: AAPL, MSFT",
                "risk_snapshot": "return=12%",
                "recent_screens": [],
            },
        }
        result = ContextBuilder.build_contextual_prompt(
            user_message="What's AAPL worth?",
            context_bundle=bundle,
            conversation_history=[],
        )
        prompt_text = result[0]["content"]
        assert "[FINANCIAL PROFILE]" in prompt_text
        assert "AAPL, MSFT" in prompt_text
        assert "WACC=10.0%" in prompt_text

    def test_no_profile_when_absent(self):
        from api.services.retrieval_service import ContextBuilder

        bundle = {
            "summaries": [],
            "tasks": [],
            "memory_facts": [],
            "messages": [],
        }
        result = ContextBuilder.build_contextual_prompt(
            user_message="Hello",
            context_bundle=bundle,
            conversation_history=[],
        )
        assert "[FINANCIAL PROFILE]" not in result[0]["content"]

    def test_empty_profile_skipped(self):
        from api.services.retrieval_service import ContextBuilder

        bundle = {
            "summaries": [],
            "tasks": [],
            "memory_facts": [],
            "messages": [],
            "financial_profile": {
                "watched_tickers": [],
                "last_dcf_assumptions": {},
                "portfolio_snapshot": None,
                "risk_snapshot": None,
                "recent_screens": [],
            },
        }
        result = ContextBuilder.build_contextual_prompt(
            user_message="Hello",
            context_bundle=bundle,
            conversation_history=[],
        )
        assert "[FINANCIAL PROFILE]" not in result[0]["content"]


# ===================================================================
# Executor memory wiring
# ===================================================================


class TestExecutorMemoryWiring:
    @pytest.mark.asyncio
    async def test_run_tool_loop_passes_user_id(self):
        """Verify extract_and_promote is called with user_id after tool execution."""
        # Build a mock invoke_fn that returns tool_calls first, then text
        call_count = 0

        async def mock_invoke(*, pid, model, payload, timeout_ms, stream):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "ok": True,
                    "result": {
                        "text": "",
                        "raw": {
                            "choices": [{
                                "finish_reason": "tool_calls",
                                "message": {
                                    "role": "assistant",
                                    "tool_calls": [{
                                        "id": "tc1",
                                        "function": {
                                            "name": "get_current_quote",
                                            "arguments": json.dumps({"ticker": "AAPL"}),
                                        },
                                    }],
                                },
                            }],
                        },
                    },
                }
            return {
                "ok": True,
                "result": {
                    "text": "AAPL is $150",
                    "raw": {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "AAPL is $150"}}]},
                },
            }

        # Mock execute_tool_call to return a non-financial result (no promotion)
        with patch("api.tools.executor.execute_tool_call", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"ticker": "AAPL", "price": 150.0}

            with patch("api.services.tool_result_memory_service.extract_and_promote", new_callable=AsyncMock) as mock_promote:
                mock_promote.return_value = []

                result = await run_tool_loop(
                    messages=[{"role": "user", "content": "Quote AAPL"}],
                    invoke_fn=mock_invoke,
                    user_id="test-user",
                    conversation_id="test-conv",
                )

                assert result["ok"]
                # extract_and_promote should have been called
                mock_promote.assert_awaited_once_with(
                    tool_name="get_current_quote",
                    tool_args={"ticker": "AAPL"},
                    tool_result={"ticker": "AAPL", "price": 150.0},
                    user_id="test-user",
                    conversation_id="test-conv",
                )

    @pytest.mark.asyncio
    async def test_run_tool_loop_skips_promotion_without_user_id(self):
        """Without user_id, promotion should not be attempted."""
        call_count = 0

        async def mock_invoke(*, pid, model, payload, timeout_ms, stream):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "ok": True,
                    "result": {
                        "text": "",
                        "raw": {
                            "choices": [{
                                "finish_reason": "tool_calls",
                                "message": {
                                    "role": "assistant",
                                    "tool_calls": [{
                                        "id": "tc1",
                                        "function": {
                                            "name": "get_current_quote",
                                            "arguments": json.dumps({"ticker": "AAPL"}),
                                        },
                                    }],
                                },
                            }],
                        },
                    },
                }
            return {
                "ok": True,
                "result": {
                    "text": "Done",
                    "raw": {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "Done"}}]},
                },
            }

        with patch("api.tools.executor.execute_tool_call", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"ticker": "AAPL", "price": 150.0}

            with patch("api.services.tool_result_memory_service.extract_and_promote", new_callable=AsyncMock) as mock_promote:
                await run_tool_loop(
                    messages=[{"role": "user", "content": "Quote AAPL"}],
                    invoke_fn=mock_invoke,
                    # No user_id → should skip promotion
                )
                mock_promote.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_run_tool_loop_skips_promotion_on_error_result(self):
        """When the tool returns an error, promotion should be skipped."""
        call_count = 0

        async def mock_invoke(*, pid, model, payload, timeout_ms, stream):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "ok": True,
                    "result": {
                        "text": "",
                        "raw": {
                            "choices": [{
                                "finish_reason": "tool_calls",
                                "message": {
                                    "role": "assistant",
                                    "tool_calls": [{
                                        "id": "tc1",
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
            return {
                "ok": True,
                "result": {
                    "text": "Error occurred",
                    "raw": {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "Error occurred"}}]},
                },
            }

        with patch("api.tools.executor.execute_tool_call", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"error": "No FCF data available"}

            with patch("api.services.tool_result_memory_service.extract_and_promote", new_callable=AsyncMock) as mock_promote:
                await run_tool_loop(
                    messages=[{"role": "user", "content": "DCF for AAPL"}],
                    invoke_fn=mock_invoke,
                    user_id="test-user",
                    conversation_id="test-conv",
                )
                # Error result → should NOT call extract_and_promote
                mock_promote.assert_not_awaited()
