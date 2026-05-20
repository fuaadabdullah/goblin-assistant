"""
Tests for sandbox template library — Phase 5.2.
"""

from __future__ import annotations

import pytest

from api.tools.sandbox_templates import (
    SandboxTemplate,
    get_template,
    list_templates,
)


class TestTemplateRegistry:
    def test_all_templates_registered(self):
        templates = list_templates()
        names = {t["name"] for t in templates}
        assert "monte_carlo_portfolio" in names
        assert "backtest_allocation" in names
        assert "compound_interest" in names

    def test_list_templates_structure(self):
        for t in list_templates():
            assert "name" in t
            assert "description" in t
            assert "parameters" in t
            assert isinstance(t["parameters"], dict)

    def test_get_template_known(self):
        t = get_template("compound_interest")
        assert t is not None
        assert t.name == "compound_interest"

    def test_get_template_unknown(self):
        assert get_template("nonexistent_template") is None


class TestMonteCarloTemplate:
    def test_render_substitutes_params(self):
        t = get_template("monte_carlo_portfolio")
        code = t.render(
            tickers="AAPL,MSFT",
            weights="0.5,0.5",
            initial_investment=10000,
            days=252,
            simulations=500,
        )
        assert '"AAPL,MSFT"' in code
        assert '"0.5,0.5"' in code
        assert "10000" in code
        assert "252" in code
        assert "500" in code

    def test_rendered_code_is_valid_python(self):
        t = get_template("monte_carlo_portfolio")
        code = t.render(
            tickers="AAPL",
            weights="1.0",
            initial_investment=5000,
            days=126,
            simulations=100,
        )
        compile(code, "<template>", "exec")  # should not raise


class TestBacktestTemplate:
    def test_render(self):
        t = get_template("backtest_allocation")
        code = t.render(
            equity_ticker="SPY",
            bond_ticker="AGG",
            equity_weight_a=0.6,
            equity_weight_b=1.0,
            period="5y",
        )
        assert "SPY" in code
        assert "AGG" in code
        assert "0.6" in code
        assert "1.0" in code

    def test_rendered_code_is_valid_python(self):
        t = get_template("backtest_allocation")
        code = t.render(
            equity_ticker="SPY",
            bond_ticker="AGG",
            equity_weight_a=0.6,
            equity_weight_b=1.0,
            period="5y",
        )
        compile(code, "<template>", "exec")


class TestCompoundInterestTemplate:
    def test_render(self):
        t = get_template("compound_interest")
        code = t.render(
            principal=10000,
            annual_rate=0.07,
            years=30,
            monthly_contribution=500,
        )
        assert "10000" in code
        assert "0.07" in code
        assert "30" in code
        assert "500" in code

    def test_rendered_code_is_valid_python(self):
        t = get_template("compound_interest")
        code = t.render(
            principal=10000,
            annual_rate=0.07,
            years=30,
            monthly_contribution=500,
        )
        compile(code, "<template>", "exec")

    def test_compound_interest_executes_correctly(self):
        """The compound interest template should produce correct math
        when actually executed (no external deps needed)."""
        t = get_template("compound_interest")
        code = t.render(
            principal=1000,
            annual_rate=0.12,
            years=1,
            monthly_contribution=0,
        )
        # Execute the code and capture printed output
        import io
        import json
        import contextlib

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(code, {"__builtins__": __builtins__})

        result = json.loads(output.getvalue())
        assert result["principal"] == 1000
        assert result["years"] == 1
        # 12% annual compounded monthly ≈ 12.68% effective
        assert 1120 < result["final_balance"] < 1130
        assert result["total_contributions"] == 1000
        assert result["total_interest"] > 0
        assert len(result["yearly_breakdown"]) == 1
