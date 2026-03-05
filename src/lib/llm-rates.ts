export interface NormalizedUsage {
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
}

export interface CostComputationResult {
  cost_usd: number;
  approx: boolean;
  source: 'backend' | 'rates';
}

// USD per 1k tokens. These are intentionally conservative defaults and may not
// match exact vendor billing.
const PROVIDER_RATES_USD_PER_1K: Record<
  string,
  { input: number; output: number }
> = {
  // Hosted APIs
  openai: { input: 0.002, output: 0.006 },
  anthropic: { input: 0.008, output: 0.024 },
  openrouter: { input: 0.003, output: 0.009 },
  groq: { input: 0.0002, output: 0.0002 },
  deepseek: { input: 0.0002, output: 0.0004 },
  gemini: { input: 0.0005, output: 0.001 },
  siliconeflow: { input: 0.001, output: 0.002 },

  // Self-hosted / local inference
  ollama_gcp: { input: 0.0, output: 0.0 },
  llamacpp_gcp: { input: 0.0, output: 0.0 },
  'goblin-chat': { input: 0.0, output: 0.0 },
};

function roundUsd(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Number(value.toFixed(6));
}

export function computeCostUsd(
  usage: NormalizedUsage | undefined,
  provider: string | undefined,
  _model?: string | undefined
): CostComputationResult {
  const p = (provider || '').trim();
  if (!usage || (!usage.total_tokens && !usage.input_tokens && !usage.output_tokens)) {
    return { cost_usd: 0, approx: true, source: 'rates' };
  }

  const rate = PROVIDER_RATES_USD_PER_1K[p] || PROVIDER_RATES_USD_PER_1K[p.replace('-', '_')];
  if (!rate) {
    // Unknown provider: fall back to a generic blended rate.
    const tokens = usage.total_tokens ?? (usage.input_tokens || 0) + (usage.output_tokens || 0);
    return { cost_usd: roundUsd((tokens / 1000) * 0.02), approx: true, source: 'rates' };
  }

  const input = usage.input_tokens ?? 0;
  const output = usage.output_tokens ?? 0;
  const total = usage.total_tokens ?? input + output;

  // If we only have total tokens, treat them as output-heavy by default.
  const inferredInput = input || (output ? 0 : Math.round(total * 0.4));
  const inferredOutput = output || (input ? 0 : total - inferredInput);

  const cost =
    (inferredInput / 1000) * rate.input + (inferredOutput / 1000) * rate.output;
  return { cost_usd: roundUsd(cost), approx: true, source: 'rates' };
}

