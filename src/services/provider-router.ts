// src/services/provider-router.ts
// Provider selection and runtime client resolution only.
// Must not contain frontend route paths or navigation logic.
type Provider = {
  endpoint?: string;
  endpoint_env?: string;
  endpoint_fallback?: string;
  api_key_env?: string | null;
  priority_tier?: number;
  capabilities?: string[];
  models?: string[];
  cost_score?: number;
  default_timeout_ms?: number;
  rate_limit_per_min?: number;
  invoke_path?: string;
};

type ProvidersMap = Record<string, Provider>;

type ProvidersConfig = {
  version: number;
  default_timeout_ms: number;
  providers: ProvidersMap;
};

type ProvidersConfigRaw = {
  version: number;
  default_timeout_ms: number;
  providers: Record<string, unknown>;
};

import providersJson from '../../config/providers.json';
import { env } from '../config/env';
import { runtimeClient, runtimeClientDemo } from '../clients';

const rawConfig = providersJson as unknown as ProvidersConfigRaw;
const PROVIDERS: ProvidersMap = Object.entries(rawConfig.providers || {}).reduce(
  (acc, [providerId, providerValue]) => {
    if (providerId.startsWith('_')) return acc;
    if (typeof providerValue !== 'object' || providerValue === null) return acc;

    const provider = providerValue as Provider;
    if (!provider.endpoint && !provider.endpoint_env) return acc;

    acc[providerId] = provider;
    return acc;
  },
  {} as ProvidersMap,
);

const config: ProvidersConfig = {
  version: rawConfig.version,
  default_timeout_ms: rawConfig.default_timeout_ms,
  providers: PROVIDERS,
};
const DEFAULT_TIMEOUT_MS = config.default_timeout_ms || 12000;

function movingAvg(arr: number[], n = 8): number | null {
  if (!arr || arr.length === 0) return null;
  const tail = arr.slice(-n);
  const sum = tail.reduce((s, currentValue) => s + currentValue, 0);
  return sum / tail.length;
}

// simple in-memory metrics mirror for UI (populated by backend telemetry if you push it)
const METRICS: Record<
  string,
  { latencies: number[]; succ: number; fail: number }
> = {};

function ensureMetrics(pid: string) {
  if (!METRICS[pid]) METRICS[pid] = { latencies: [], succ: 0, fail: 0 };
}

export function updateMetricsFromBackend(
  pid: string,
  latencyMs: number,
  ok: boolean,
) {
  ensureMetrics(pid);
  METRICS[pid].latencies.push(latencyMs);
  if (METRICS[pid].latencies.length > 100) METRICS[pid].latencies.shift();
  if (ok) METRICS[pid].succ += 1;
  else METRICS[pid].fail += 1;
}

function scoreProvider(
  pid: string,
  capability: string,
  preferLocal = false,
  preferCost = false,
): number {
  const p = PROVIDERS[pid] as Provider;
  if (!p.capabilities || p.capabilities.indexOf(capability) === -1)
    return Infinity;

  let score = 0;

  // Priority tier component (default to 2 if missing)
  const priorityTier =
    typeof p.priority_tier === 'number' && !isNaN(p.priority_tier)
      ? p.priority_tier
      : 2;
  score += priorityTier * 10;

  // Cost component (default to 0.5 if missing)
  const costScore =
    typeof p.cost_score === 'number' && !isNaN(p.cost_score)
      ? p.cost_score
      : 0.5;
  score += costScore * 5;

  // Latency component
  const avgLatency = movingAvg(METRICS[pid]?.latencies || []);
  const defaultLatency =
    typeof p.default_timeout_ms === 'number' && !isNaN(p.default_timeout_ms)
      ? p.default_timeout_ms
      : DEFAULT_TIMEOUT_MS;
  const lat = avgLatency ?? defaultLatency / 2;
  score += (lat / 1000) * 2;

  // Success rate component
  const succ = METRICS[pid]?.succ || 0;
  const fail = METRICS[pid]?.fail || 0;
  const total = succ + fail;
  const succRate = total > 0 ? succ / total : 0.9;
  score *= 1 - succRate * 0.45;

  // Local preference
  if (preferLocal && (p.endpoint || '').startsWith('http://127.0.0.1'))
    score *= 0.6;

  // Cost preference
  if (preferCost) score += costScore * 10;

  // Small random component for tie-breaking
  score += Math.random() * 0.01;

  // Final validation - ensure we return a valid number
  return !isNaN(score) && isFinite(score) ? score : Infinity;
}

export function topProvidersFor(
  capability: string,
  preferLocal = false,
  preferCost = false,
  limit = 6,
): string[] {
  const items: [number, string][] = [];
  Object.keys(PROVIDERS).forEach((pid) => {
    try {
      const s = scoreProvider(pid, capability, preferLocal, preferCost);
      if (s !== Infinity) items.push([s, pid]);
    } catch (e) {
      // ignore
    }
  });
  items.sort((a, b) => a[0] - b[0]);
  return items.slice(0, limit).map((x) => x[1]);
}

export function getRuntimeClient() {
  return env.mockApi ? runtimeClientDemo : runtimeClient;
}

export default {
  topProvidersFor,
  updateMetricsFromBackend,
  getRuntimeClient,
};
