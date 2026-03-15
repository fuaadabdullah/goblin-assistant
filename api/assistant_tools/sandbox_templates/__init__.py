"""
Sandbox template library for Goblin Assistant.

Pre-built, LLM-invokable Python templates for common financial analyses.
Each template is a parameterized Python script that can run inside the
Docker sandbox with yfinance, pandas, numpy, and matplotlib available.
"""

from __future__ import annotations

import inspect
import textwrap
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------

_TEMPLATES: Dict[str, "SandboxTemplate"] = {}


class SandboxTemplate:
    """A parameterized Python script template."""

    name: str
    description: str
    parameters: Dict[str, str]  # param_name -> description
    _source: str  # Python source with {param} placeholders

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, str],
        source: str,
    ) -> None:
        self.name = name
        self.description = description
        self.parameters = parameters
        self._source = textwrap.dedent(source).strip()
        _TEMPLATES[name] = self

    def render(self, **kwargs: Any) -> str:
        """Fill in template parameters and return executable Python code."""
        code = self._source
        for key, value in kwargs.items():
            code = code.replace(f"{{{key}}}", str(value))
        return code


def get_template(name: str) -> Optional[SandboxTemplate]:
    return _TEMPLATES.get(name)


def list_templates() -> List[Dict[str, Any]]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "parameters": t.parameters,
        }
        for t in _TEMPLATES.values()
    ]


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

SandboxTemplate(
    name="monte_carlo_portfolio",
    description=(
        "Run a Monte Carlo simulation on a portfolio to estimate the "
        "distribution of future returns over a specified horizon."
    ),
    parameters={
        "tickers": "Comma-separated ticker symbols, e.g. AAPL,MSFT,GOOGL",
        "weights": "Comma-separated weights summing to 1.0, e.g. 0.4,0.3,0.3",
        "initial_investment": "Starting portfolio value in USD",
        "days": "Number of trading days to simulate (252 = 1 year)",
        "simulations": "Number of Monte Carlo paths (e.g. 1000)",
    },
    source="""
        import numpy as np
        import yfinance as yf
        import json

        tickers = "{tickers}".split(",")
        weights = np.array([float(w) for w in "{weights}".split(",")])
        initial = float({initial_investment})
        days = int({days})
        n_sims = int({simulations})

        # Fetch 2 years of daily closes
        data = yf.download(tickers, period="2y", interval="1d", progress=False)["Close"]
        if data.ndim == 1:
            data = data.to_frame()
        returns = data.pct_change().dropna()

        mean_ret = returns.mean().values
        cov_matrix = returns.cov().values

        results = []
        for _ in range(n_sims):
            daily = np.random.multivariate_normal(mean_ret, cov_matrix, days)
            port_daily = daily @ weights
            cumulative = initial * np.cumprod(1 + port_daily)
            results.append(float(cumulative[-1]))

        results = sorted(results)
        p5 = results[int(n_sims * 0.05)]
        p50 = results[int(n_sims * 0.50)]
        p95 = results[int(n_sims * 0.95)]
        mean_final = float(np.mean(results))

        output = {
            "initial_investment": initial,
            "days": days,
            "simulations": n_sims,
            "percentile_5": round(p5, 2),
            "percentile_50": round(p50, 2),
            "percentile_95": round(p95, 2),
            "mean_final_value": round(mean_final, 2),
            "mean_return_pct": round((mean_final / initial - 1) * 100, 2),
            "probability_of_loss": round(sum(1 for r in results if r < initial) / n_sims * 100, 2),
        }
        print(json.dumps(output, indent=2))
    """,
)


SandboxTemplate(
    name="backtest_allocation",
    description=(
        "Backtest two portfolio allocations (e.g. 60/40 bonds vs 100% equity) "
        "over a historical period and compare cumulative returns."
    ),
    parameters={
        "equity_ticker": "Equity ETF ticker (e.g. SPY)",
        "bond_ticker": "Bond ETF ticker (e.g. AGG)",
        "equity_weight_a": "Equity weight for Portfolio A (e.g. 0.6)",
        "equity_weight_b": "Equity weight for Portfolio B (e.g. 1.0)",
        "period": "Lookback period (e.g. 5y, 10y)",
    },
    source="""
        import numpy as np
        import yfinance as yf
        import json

        eq_ticker = "{equity_ticker}"
        bond_ticker = "{bond_ticker}"
        eq_w_a = float({equity_weight_a})
        eq_w_b = float({equity_weight_b})
        period = "{period}"

        data = yf.download([eq_ticker, bond_ticker], period=period, interval="1d", progress=False)["Close"]
        data = data.dropna()
        returns = data.pct_change().dropna()

        port_a = returns[eq_ticker] * eq_w_a + returns[bond_ticker] * (1 - eq_w_a)
        port_b = returns[eq_ticker] * eq_w_b + returns[bond_ticker] * (1 - eq_w_b)

        cum_a = (1 + port_a).cumprod()
        cum_b = (1 + port_b).cumprod()

        def stats(rets, cum):
            ann_ret = (cum.iloc[-1]) ** (252 / len(rets)) - 1
            vol = rets.std() * np.sqrt(252)
            sharpe = (ann_ret - 0.043) / vol if vol > 0 else 0
            peak = cum.cummax()
            dd = ((peak - cum) / peak).max()
            return {
                "annualized_return_pct": round(float(ann_ret * 100), 2),
                "annualized_volatility_pct": round(float(vol * 100), 2),
                "sharpe_ratio": round(float(sharpe), 2),
                "max_drawdown_pct": round(float(dd * 100), 2),
                "cumulative_return_pct": round(float((cum.iloc[-1] - 1) * 100), 2),
            }

        output = {
            "period": period,
            "portfolio_a": {
                "label": f"{int(eq_w_a*100)}/{int((1-eq_w_a)*100)} {eq_ticker}/{bond_ticker}",
                **stats(port_a, cum_a),
            },
            "portfolio_b": {
                "label": f"{int(eq_w_b*100)}/{int((1-eq_w_b)*100)} {eq_ticker}/{bond_ticker}",
                **stats(port_b, cum_b),
            },
        }
        print(json.dumps(output, indent=2))
    """,
)


SandboxTemplate(
    name="compound_interest",
    description=(
        "Calculate compound interest over a specified number of years with "
        "optional regular contributions. Shows year-by-year growth."
    ),
    parameters={
        "principal": "Initial investment in USD",
        "annual_rate": "Annual interest rate as decimal (e.g. 0.07 for 7%)",
        "years": "Number of years to compound",
        "monthly_contribution": "Monthly additional contribution in USD (0 if none)",
    },
    source="""
        import json

        principal = float({principal})
        rate = float({annual_rate})
        years = int({years})
        monthly = float({monthly_contribution})
        monthly_rate = rate / 12

        balance = principal
        total_contributions = principal
        yearly_data = []

        for year in range(1, years + 1):
            for _ in range(12):
                balance = balance * (1 + monthly_rate) + monthly
                total_contributions += monthly
            yearly_data.append({
                "year": year,
                "balance": round(balance, 2),
                "total_contributions": round(total_contributions, 2),
                "interest_earned": round(balance - total_contributions, 2),
            })

        output = {
            "principal": principal,
            "annual_rate_pct": round(rate * 100, 2),
            "years": years,
            "monthly_contribution": monthly,
            "final_balance": round(balance, 2),
            "total_contributions": round(total_contributions, 2),
            "total_interest": round(balance - total_contributions, 2),
            "yearly_breakdown": yearly_data,
        }
        print(json.dumps(output, indent=2))
    """,
)
