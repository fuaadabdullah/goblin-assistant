export type CostFormatMode = 'summary' | 'per-message' | 'per-token';

interface FormatCostOptions {
  mode?: CostFormatMode;
}

const COST_PRECISION: Record<CostFormatMode, number> = {
  summary: 2,
  'per-message': 4,
  'per-token': 6,
};

export const formatCost = (usd: number, opts: FormatCostOptions = {}): string => {
  const mode = opts.mode ?? 'summary';
  const precision = COST_PRECISION[mode];
  return `$${usd.toFixed(precision)}`;
};
