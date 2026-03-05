import { computeCostUsd } from '../llm-rates';

describe('computeCostUsd', () => {
  test('returns 0 for missing usage', () => {
    expect(computeCostUsd(undefined, 'openai').cost_usd).toBe(0);
  });

  test('computes a conservative estimate from total tokens when split is missing', () => {
    const r = computeCostUsd({ total_tokens: 1000 }, 'openai');
    // 40% input at $0.002/1k + 60% output at $0.006/1k = 0.0044
    expect(r.cost_usd).toBeCloseTo(0.0044, 6);
    expect(r.approx).toBe(true);
    expect(r.source).toBe('rates');
  });
});

