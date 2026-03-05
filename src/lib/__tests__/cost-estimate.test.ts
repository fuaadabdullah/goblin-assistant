import { estimateFromText } from '../cost-estimate';

describe('estimateFromText', () => {
  test('returns zeros for empty input', () => {
    expect(estimateFromText('')).toEqual({ estimated_tokens: 0, estimated_cost_usd: 0 });
    expect(estimateFromText('   ')).toEqual({ estimated_tokens: 0, estimated_cost_usd: 0 });
  });

  test('enforces a minimum token estimate and computes cost', () => {
    const est = estimateFromText('hi');
    expect(est.estimated_tokens).toBeGreaterThanOrEqual(8);
    expect(est.estimated_cost_usd).toBeGreaterThan(0);
  });
});

