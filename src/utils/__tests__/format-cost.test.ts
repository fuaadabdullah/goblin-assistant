import { formatCost } from '../format-cost';

describe('formatCost', () => {
  it('formats summary values to two decimals', () => {
    expect(formatCost(12.3456, { mode: 'summary' })).toBe('$12.35');
  });

  it('formats per-message values to four decimals', () => {
    expect(formatCost(0.01234, { mode: 'per-message' })).toBe('$0.0123');
  });

  it('formats per-token values to six decimals', () => {
    expect(formatCost(0.0001234, { mode: 'per-token' })).toBe('$0.000123');
  });

  it('defaults to summary mode', () => {
    expect(formatCost(0)).toBe('$0.00');
  });

  it('preserves sign for negative values', () => {
    expect(formatCost(-1.2345, { mode: 'summary' })).toBe('$-1.23');
  });
});
