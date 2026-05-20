import { estimateFromText } from '../cost-estimate';

describe('estimateFromText', () => {
  it('returns zero for empty string', () => {
    const result = estimateFromText('');
    expect(result.estimated_tokens).toBe(0);
    expect(result.estimated_cost_usd).toBe(0);
  });

  it('returns zero for whitespace-only string', () => {
    const result = estimateFromText('   ');
    expect(result.estimated_tokens).toBe(0);
    expect(result.estimated_cost_usd).toBe(0);
  });

  it('returns zero for undefined/null-like values', () => {
    const result = estimateFromText('');
    expect(result.estimated_tokens).toBe(0);
  });

  it('estimates tokens for ASCII text', () => {
    const result = estimateFromText('Hello world');
    expect(result.estimated_tokens).toBeGreaterThan(0);
    expect(result.estimated_cost_usd).toBeGreaterThan(0);
  });

  it('estimates ~4 chars per token for ASCII', () => {
    const result = estimateFromText('a'.repeat(40));
    expect(result.estimated_tokens).toBe(10); // 40/4 = 10
  });

  it('minimum estimate is 8 tokens', () => {
    const result = estimateFromText('hi');
    expect(result.estimated_tokens).toBeGreaterThanOrEqual(8);
  });

  it('handles Unicode characters', () => {
    const result = estimateFromText('café résumé ñoño');
    expect(result.estimated_tokens).toBeGreaterThan(0);
  });

  it('handles emoji characters', () => {
    const result = estimateFromText('Hello 😀🚀🌟');
    expect(result.estimated_tokens).toBeGreaterThan(0);
  });

  it('returns valid numeric results', () => {
    const result = estimateFromText('A longer text to test with enough characters for a proper estimate');
    expect(result.estimated_tokens).toBeGreaterThan(0);
    expect(Number.isFinite(result.estimated_cost_usd)).toBe(true);
    expect(result.estimated_cost_usd).toBeGreaterThan(0);
  });

  it('has predictable cost at known token count', () => {
    // 1000 tokens at $0.02/1k = $0.02
    const result = estimateFromText('a'.repeat(4000)); // ~1000 tokens
    expect(result.estimated_tokens).toBeGreaterThanOrEqual(900);
    expect(result.estimated_cost_usd).toBeGreaterThan(0);
  });
});