'use client';

import { useState } from 'react';
import AnalystQuickQuote from './AnalystQuickQuote';
import FinancialVisualization from '../finance/FinancialVisualization';

interface QuoteData {
  ticker: string;
  price: number;
  change: number;
  percentChange: number;
  marketCap?: string;
  volume?: number;
  high?: number;
  low?: number;
}

// Example watchlist data for initial display
const DEFAULT_WATCHLIST: QuoteData[] = [
  {
    ticker: 'AAPL',
    price: 198.5,
    change: 1.25,
    percentChange: 0.63,
    marketCap: '$3.05T',
    volume: 45200000,
    high: 199.8,
    low: 197.1,
  },
  {
    ticker: 'NVDA',
    price: 875.3,
    change: -4.2,
    percentChange: -0.48,
    marketCap: '$2.15T',
    volume: 38500000,
    high: 884.5,
    low: 870.1,
  },
  {
    ticker: 'MSFT',
    price: 425.1,
    change: 2.8,
    percentChange: 0.66,
    marketCap: '$3.16T',
    volume: 22100000,
    high: 427.3,
    low: 422.4,
  },
  {
    ticker: 'GOOGL',
    price: 175.4,
    change: 0.9,
    percentChange: 0.52,
    marketCap: '$2.18T',
    volume: 18300000,
    high: 176.5,
    low: 174.2,
  },
  {
    ticker: 'AMZN',
    price: 198.2,
    change: 1.5,
    percentChange: 0.76,
    marketCap: '$2.06T',
    volume: 31500000,
    high: 199.4,
    low: 196.8,
  },
];

interface AnalystViewProps {
  watchlist?: QuoteData[];
}

const AnalystView = ({ watchlist = DEFAULT_WATCHLIST }: AnalystViewProps) => {
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-text">📊 Analyst</h2>
        <p className="text-muted mt-1">
          Market data, portfolio analytics, earnings, and financial research
        </p>
      </div>

      {/* Stock Search */}
      <div className="relative">
        <input
          type="text"
          placeholder="Search ticker (e.g., AAPL, NVDA, MSFT)..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value.toUpperCase())}
          className="w-full rounded-xl border border-border bg-surface/70 px-4 py-3 pl-10 text-text placeholder:text-muted focus:border-primary focus:outline-none"
        />
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted">🔍</span>
      </div>

      {/* Watchlist / Quote Cards */}
      {watchlist.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-text mb-3">Watchlist</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {watchlist.map((quote) => (
              <AnalystQuickQuote key={quote.ticker} quote={quote} />
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <button
          type="button"
          className="rounded-xl border border-border bg-surface/70 p-4 text-center hover:border-primary/50 transition-colors"
        >
          <div className="text-xl mb-1">📈</div>
          <div className="text-sm font-medium text-text">Market Overview</div>
        </button>
        <button
          type="button"
          className="rounded-xl border border-border bg-surface/70 p-4 text-center hover:border-primary/50 transition-colors"
        >
          <div className="text-xl mb-1">💼</div>
          <div className="text-sm font-medium text-text">Portfolio</div>
        </button>
        <button
          type="button"
          className="rounded-xl border border-border bg-surface/70 p-4 text-center hover:border-primary/50 transition-colors"
        >
          <div className="text-xl mb-1">🏷️</div>
          <div className="text-sm font-medium text-text">Stock Screener</div>
        </button>
        <button
          type="button"
          className="rounded-xl border border-border bg-surface/70 p-4 text-center hover:border-primary/50 transition-colors"
        >
          <div className="text-xl mb-1">📰</div>
          <div className="text-sm font-medium text-text">Market News</div>
        </button>
      </div>

      {/* Financial Visualization Area (placeholder) */}
      <div className="rounded-xl border border-border bg-surface/70 p-4">
        <p className="text-muted text-sm text-center">
          Ask the analyst a question in chat to see interactive visualizations, screeners, and
          portfolio analytics here.
        </p>
      </div>
    </div>
  );
};

export default AnalystView;
