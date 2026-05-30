# Financial Analyst — User Guide

Goblin Assistant includes a built-in **Financial Analyst** powered by real market data. Ask questions in plain English and get structured answers with interactive charts.

---

## What can it do?

### 1. DCF Valuation
> "What's Apple worth based on a DCF model?"
>
> "Run a DCF on MSFT with 8% growth and 10% WACC"

Returns intrinsic value per share, upside/downside vs current price, projected free cash flows, and a WACC × growth sensitivity matrix.

### 2. Portfolio Analysis
> "Analyze my portfolio: 50% AAPL, 30% GOOGL, 20% AMZN"
>
> "How does my portfolio compare to SPY?"

Returns allocation breakdown, annualized return & volatility, Sharpe ratio, max drawdown, Value-at-Risk, and a correlation heatmap.

### 3. Earnings Summary
> "How were NVDA's last 4 earnings?"
>
> "Did Tesla beat or miss earnings?"

Returns beat/miss verdicts per quarter, EPS estimate vs actual, surprise %, streak analysis, and key valuation metrics.

### 4. Stock Screener
> "Find large-cap stocks with P/E under 20 and dividend yield above 2%"
>
> "Screen tech stocks with ROE above 15%"

Screens 50 major stocks against your criteria and returns ranked results with key metrics.

### 5. Market Data
> "What's the current price of AAPL?"
>
> "Show me TSLA's price history for the last 6 months"

Fetches real-time quotes, historical OHLCV data, financial statements, earnings data, and key ratios.

---

## Visualizations

Financial tool results are automatically rendered as interactive charts:

| Tool | Visualizations |
|------|---------------|
| DCF Calculator | Bar chart (FCF projections), Sensitivity table, Valuation summary |
| Portfolio Analyzer | Pie chart (allocation), Bar chart (risk/return), Correlation heatmap, Risk summary |
| Earnings Summarizer | Bar chart (EPS estimate vs actual), Key metrics table |
| Stock Screener | Results table, Market cap comparison chart |

Charts appear inline below the assistant's text response.

---

## Sandbox Templates

For advanced analysis, ask the assistant to run one of these pre-built templates in the code sandbox:

### Monte Carlo Simulation
> "Run a Monte Carlo simulation on AAPL and MSFT with equal weights, $10k initial investment"

Simulates thousands of portfolio paths to estimate the distribution of future returns.

### Portfolio Backtest
> "Backtest a 60/40 portfolio vs 100% stocks over the last 5 years"

Compares two allocation strategies using historical data with risk-adjusted metrics.

### Compound Interest Calculator
> "Calculate compound interest on $10,000 at 7% for 30 years with $500 monthly contributions"

Shows year-by-year growth with contributions vs interest breakdown.

---

## Tips

- **Ticker format**: Use standard symbols like `AAPL`, `MSFT`, `GOOGL`, `BRK.B`
- **Be specific**: "DCF on AAPL with 12% WACC" works better than "value some stock"
- **Combine tools**: "Value AAPL and then compare it to its earnings history" will invoke multiple tools
- **Memory**: The assistant remembers your past analyses. It may reference previous WACC assumptions or portfolio holdings.

## Rate Limits

Financial data is fetched from market data providers with caching:
- Quotes: cached 15 minutes
- Financials/earnings/ratios: cached 24 hours
- Price history: cached 1 hour

If you hit the rate limit, wait a moment and try again.
