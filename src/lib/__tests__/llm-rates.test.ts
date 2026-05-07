import { computeCostUsd } from '../llm-rates';

describe('computeCostUsd', () => {
  it('returns zero when usage is undefined', () => {
    const result = computeCostUsd(undefined, 'openai');
    expect(result.cost_usd).toBe(0);
    expect(result.approx).toBe(true);
    expect(result.source).toBe('rates');
  });

  it('returns zero when usage has no tokens', () => {
    const result = computeCostUsd({}, 'openai');
    expect(result.cost_usd).toBe(0);
    expect(result.approx).toBe(true);
  });

  it('computes cost for openai with input and output tokens', () => {
    const result = computeCostUsd({ input_tokens: 1000, output_tokens: 500 }, 'openai');
    // input: 1000 * 0.002/1k = 0.002, output: 500 * 0.006/1k = 0.003
    expect(result.cost_usd).toBe(0.005);
  });

  it('computes cost for anthropic with higher rates', () => {
    const result = computeCostUsd({ input_tokens: 1000, output_tokens: 500 }, 'anthropic');
    // input: 1000 * 0.008/1k = 0.008, output: 500 * 0.024/1k = 0.012
    expect(result.cost_usd).toBe(0.02);
  });

  it('handles total_tokens only', () => {
    const result = computeCostUsd({ total_tokens: 1500 }, 'openai');
    // inferredInput = 1500 * 0.4 = 600, inferredOutput = 900
    expect(result.cost_usd).toBeGreaterThan(0);
  });

  it('handles unknown provider with generic rate', () => {
    const result = computeCostUsd({ total_tokens: 1000 }, 'unknown-provider');
    expect(result.cost_usd).toBe(0.02); // 1000/1000 * 0.02 = 0.02
  });

  it('handles self-hosted provider with zero rates', () => {
    const result = computeCostUsd({ input_tokens: 1000, output_tokens: 500 }, 'ollama_gcp');
    expect(result.cost_usd).toBe(0);
  });

  it('handles goblin-chat provider with zero rates', () => {
    const result = computeCostUsd({ input_tokens: 1000, output_tokens: 500 }, 'goblin-chat');
    expect(result.cost_usd).toBe(0);
  });

  it('handles groq provider', () => {
    const result = computeCostUsd({ input_tokens: 1000, output_tokens: 1000 }, 'groq');
    // input: 1000 * 0.0002/1k = 0.0002, output: 1000 * 0.0002/1k = 0.0002
    expect(result.cost_usd).toBe(0.0004);
  });

  it('handles gemini provider', () => {
    const result = computeCostUsd({ input_tokens: 1000, output_tokens: 1000 }, 'gemini');
    expect(result.cost_usd).toBeGreaterThan(0);
  });

  it('handles undefined provider with generic blended rate', () => {
    const result = computeCostUsd({ total_tokens: 500 }, undefined);
    expect(result.cost_usd).toBe(0.01); // 500/1000 * 0.02 = 0.01
  });

  it('rounds to 6 decimal places', () => {
    const result = computeCostUsd({ input_tokens: 333, output_tokens: 667 }, 'openai');
    expect(result.cost_usd.toString()).not.toContain('e');
  });

  it('returns zero for zero tokens', () => {
    const result = computeCostUsd({ input_tokens: 0, output_tokens: 0 }, 'openai');
    expect(result.cost_usd).toBe(0);
  });
});