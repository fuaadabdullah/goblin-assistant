// src/services/provider-router.ts
// Provider selection and runtime client resolution only.
// Must not contain frontend route paths or navigation logic.
//
// Config is loaded from config/providers.json, which is a generated artifact
// from config/providers.toml (the single source of truth).
// Run `make generate-providers-json` after editing providers.toml.

import providersJson from '../config/providers.json';
import { runtimeClient } from '@/api';

// ── Minimal runtime types (mirrored from shared schema) ──────────────────
interface JsonProviderEntry {
  endpoint?: string;
  endpoint_env?: string | null;
  endpoint_fallback?: string | null;
  api_key_env?: string | null;
  priority_tier?: number;
  capabilities?: string[];
  models?: string[];
  cost_score?: number;
  default_timeout_ms?: number;
  rate_limit_per_min?: number;
  display_name?: string;
  is_active?: boolean;
  invoke_path?: string | null;
}

interface ProvidersJson {
  version: number;
  default_timeout_ms: number;
  providers: Record<string, JsonProviderEntry>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isNumber(value: unknown): value is number {
  return typeof value === 'number' && !Number.isNaN(value);
}

function validateProvidersJson(raw: unknown): ProvidersJson {
  if (!isRecord(raw)) {
    throw new Error('providers.json: root must be an object');
  }

  const version = raw.version;
  if (version !== 2) {
    throw new Error(`providers.json: expected version=2, got ${String(version)}`);
  }

  const defaultTimeout = raw.default_timeout_ms;
  if (!isNumber(defaultTimeout) || defaultTimeout <= 0) {
    throw new Error(
      `providers.json: invalid default_timeout_ms: ${String(defaultTimeout)}`
    );
  }

  if (!isRecord(raw.providers)) {
    throw new Error('providers.json: providers must be an object');
  }

  return raw as unknown as ProvidersJson;
}

let config: ProvidersJson;
try {
  config = validateProvidersJson(providersJson);
  // Validate that required provider fields exist
  Object.entries(config.providers || {}).forEach(([id, provider]) => {
    const p = provider as unknown as JsonProviderEntry;
    if (!p.capabilities || p.capabilities.length === 0) {
      console.warn(
        `Provider schema mismatch: ${id} missing or empty 'capabilities' field`
      );
    }
  });
  console.debug('Provider config validated successfully');
} catch (validationError) {
  console.error(
    'Provider config validation failed:',
    validationError instanceof Error ? validationError.message : String(validationError)
  );
  // Fallback to empty config to prevent startup crash
  config = { providers: {} } as ProvidersJson;
}

const PROVIDERS = config.providers || {};
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
  const p = PROVIDERS[pid] as unknown as JsonProviderEntry;
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
  return runtimeClient;
}

export default {
  topProvidersFor,
  updateMetricsFromBackend,
  getRuntimeClient,
};
