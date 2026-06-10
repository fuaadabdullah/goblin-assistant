/**
 * Feature flags configuration
 * Controls which features are enabled in the application
 */

import { env } from './env';
import { devWarn } from '../utils/dev-log';

export interface FeatureFlags {
  ragEnabled: boolean;
  multiProvider: boolean;
  passkeyAuth: boolean;
  googleAuth: boolean;
  orchestration: boolean;
  sandbox: boolean;
  search: boolean;
  admin: boolean;
  analytics: boolean;
  debugMode: boolean;
}

export interface ModuleFlags {
  sandbox: boolean;
  search: boolean;
  admin: boolean;
}

export type ExperimentVariant = string;

export interface Experiment {
  name: string;
  variants: readonly ExperimentVariant[];
  /** Per-variant weights that sum to 1. Equal split when omitted. */
  weights?: readonly number[] | undefined;
}

const FLAG_STORAGE_PREFIX = 'goblin:flag:';
const EXPERIMENT_STORAGE_PREFIX = 'goblin:exp:';

// Load from centralized environment configuration
export const featureFlags: FeatureFlags = env.features;

export const moduleFlags: ModuleFlags = {
  sandbox: featureFlags.sandbox,
  search: featureFlags.search,
  admin: featureFlags.admin,
};

/** Static env-based flag check — safe on server. */
export const isFeatureEnabled = (feature: keyof FeatureFlags): boolean => featureFlags[feature];

/**
 * Runtime flag check — reads a localStorage override if present so QA and
 * developers can toggle flags without a redeploy.  Falls back to the env-based
 * value.  Returns the static value on the server (no localStorage).
 */
export const getRuntimeFlag = (feature: keyof FeatureFlags): boolean => {
  if (typeof window === 'undefined') return featureFlags[feature];
  const stored = window.localStorage.getItem(`${FLAG_STORAGE_PREFIX}${feature}`);
  if (stored === 'true') return true;
  if (stored === 'false') return false;
  return featureFlags[feature];
};

/** Persist a runtime override to localStorage (client only). */
export const setRuntimeFlag = (feature: keyof FeatureFlags, enabled: boolean): void => {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(`${FLAG_STORAGE_PREFIX}${feature}`, String(enabled));
};

/** Remove a single runtime override, restoring the env-based default. */
export const clearRuntimeFlag = (feature: keyof FeatureFlags): void => {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(`${FLAG_STORAGE_PREFIX}${feature}`);
};

/** Remove all runtime flag overrides. */
export const clearAllRuntimeFlags = (): void => {
  if (typeof window === 'undefined') return;
  Object.keys(window.localStorage)
    .filter((k) => k.startsWith(FLAG_STORAGE_PREFIX))
    .forEach((k) => window.localStorage.removeItem(k));
};

// ── Experiment support ──────────────────────────────────────────────────────

/** djb2 hash — deterministic, fast, no crypto dependency. */
function djb2(s: string): number {
  let hash = 5381;
  for (let i = 0; i < s.length; i++) {
    hash = ((hash << 5) + hash) ^ s.charCodeAt(i);
  }
  return Math.abs(hash);
}

/**
 * Returns a stable experiment variant for the given user.
 *
 * Bucketing is deterministic: the same `userId` + `experiment.name` always
 * maps to the same variant, so a user never switches cohorts across sessions.
 *
 * A localStorage override (`goblin:exp:<name>`) lets developers force a variant
 * without changing their user ID.
 */
export const getExperimentVariant = (experiment: Experiment, userId: string): ExperimentVariant => {
  if (typeof window !== 'undefined') {
    const override = window.localStorage.getItem(`${EXPERIMENT_STORAGE_PREFIX}${experiment.name}`);
    if (override !== null && experiment.variants.includes(override)) return override;
  }

  const { variants, weights } = experiment;
  const hash = djb2(`${userId}:${experiment.name}`);

  if (weights && weights.length === variants.length) {
    const normalized = (hash % 10000) / 10000; // [0, 1)
    let cumulative = 0;
    for (let i = 0; i < variants.length; i++) {
      cumulative += weights[i] ?? 0;
      if (normalized < cumulative) return variants[i]!;
    }
    return variants[variants.length - 1]!;
  }

  return variants[hash % variants.length]!;
};

/** Force a specific variant for manual testing (client only). */
export const setExperimentOverride = (experimentName: string, variant: string): void => {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(`${EXPERIMENT_STORAGE_PREFIX}${experimentName}`, variant);
};

/** Remove a forced experiment variant. */
export const clearExperimentOverride = (experimentName: string): void => {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(`${EXPERIMENT_STORAGE_PREFIX}${experimentName}`);
};

export const getEnabledModules = (): ModuleFlags => moduleFlags;

// Log enabled features in development
if (env.isDevelopment && featureFlags.debugMode) {
  devWarn('🚩 Feature Flags:', featureFlags);
}
