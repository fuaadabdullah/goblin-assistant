'use client';

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

interface AnalystQuickQuoteProps {
  quote: QuoteData;
}

const formatChange = (value: number) => {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}`;
};

const AnalystQuickQuote = ({ quote }: AnalystQuickQuoteProps) => {
  const isPositive = quote.change >= 0;
  const changeColor = isPositive ? 'text-green-600' : 'text-red-600';

  return (
    <div className="rounded-xl border border-border bg-surface/70 p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-text">{quote.ticker.toUpperCase()}</h3>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-text">${quote.price.toFixed(2)}</div>
          <div className={`text-sm font-medium ${changeColor}`}>
            {formatChange(quote.change)} ({formatChange(quote.percentChange)}%)
          </div>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-muted">
        {quote.marketCap && (
          <div>
            <span className="block uppercase tracking-wide">Mkt Cap</span>
            <span className="font-semibold text-text">{quote.marketCap}</span>
          </div>
        )}
        {quote.volume && (
          <div>
            <span className="block uppercase tracking-wide">Volume</span>
            <span className="font-semibold text-text">{quote.volume.toLocaleString()}</span>
          </div>
        )}
        {quote.high && quote.low && (
          <div>
            <span className="block uppercase tracking-wide">Day Range</span>
            <span className="font-semibold text-text">
              ${quote.low.toFixed(2)} – ${quote.high.toFixed(2)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default AnalystQuickQuote;