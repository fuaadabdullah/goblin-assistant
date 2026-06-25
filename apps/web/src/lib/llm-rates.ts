import { providerRateLookupKeys } from './providers/normalizeProvider';

export interface NormalizedUsage {
  input_tokens?: number | undefined;
  output_tokens?: number | undefined;
  total_tokens?: number | undefined;
}

export interface CostComputationResult {
  cost_usd: number;
  approx: boolean;
  source: 'backend' | 'rates';
}

// USD per 1k tokens. These are intentionally conservative defaults and may not
// match exact vendor billing.
const PROVIDER_RATES_USD_PER_1K: Record<string, { input: number; output: number }> = {
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

const getKnownRate = (provider: string | undefined) => {
  const keys = providerRateLookupKeys(provider);
  return keys.map((key) => PROVIDER_RATES_USD_PER_1K[key]).find((candidate) => Boolean(candidate));
};

const computeFallbackCost = (usage: NormalizedUsage): number => {
  const tokens = usage.total_tokens ?? (usage.input_tokens || 0) + (usage.output_tokens || 0);
  return roundUsd((tokens / 1000) * 0.02);
};

const inferUsageSplit = (usage: NormalizedUsage, rate: { input: number; output: number }) => {
  const input = usage.input_tokens ?? 0;
  const output = usage.output_tokens ?? 0;
  const total = usage.total_tokens ?? input + output;
  const inferredInput = input || (output ? 0 : Math.round(total * 0.4));
  const inferredOutput = output || (input ? 0 : total - inferredInput);

  return {
    inferredInput,
    inferredOutput,
    cost: (inferredInput / 1000) * rate.input + (inferredOutput / 1000) * rate.output,
  };
};

export function computeCostUsd(
  usage: NormalizedUsage | undefined,
  provider: string | undefined,
  modelName?: string | undefined
): CostComputationResult {
  void modelName;

  if (!usage || (!usage.total_tokens && !usage.input_tokens && !usage.output_tokens)) {
    return { cost_usd: 0, approx: true, source: 'rates' };
  }

  const rate = getKnownRate(provider);
  if (!rate) {
    // Unknown provider: fall back to a generic blended rate.
    return { cost_usd: computeFallbackCost(usage), approx: true, source: 'rates' };
  }

  const { cost } = inferUsageSplit(usage, rate);
  return { cost_usd: roundUsd(cost), approx: true, source: 'rates' };
}
