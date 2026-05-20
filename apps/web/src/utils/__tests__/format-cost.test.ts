import { formatCost } from '../format-cost';

describe('formatCost', () => {
  it('formats zero cost with default summary mode', () => {
    expect(formatCost(0)).toBe('$0.00');
  });

  it('formats cost with summary precision (2 decimals)', () => {
    expect(formatCost(1.5)).toBe('$1.50');
  });

  it('formats cost with per-message precision (4 decimals)', () => {
    expect(formatCost(0.005, { mode: 'per-message' })).toBe('$0.0050');
  });

  it('formats cost with per-token precision (6 decimals)', () => {
    expect(formatCost(0.000123, { mode: 'per-token' })).toBe('$0.000123');
  });

  it('defaults to summary mode when no options provided', () => {
    expect(formatCost(0.005)).toBe('$0.01');
  });
});
