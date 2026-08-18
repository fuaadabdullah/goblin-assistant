/**
 * Feature flags configuration
 * Controls which features are enabled in the application
 */

import { env } from './env';
import { devLog } from '../utils/dev-log';

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

export interface Experiment {
  name: string;
  variants: readonly string[];
}

export type ExperimentVariant = string;

// Load from centralized environment configuration
export const featureFlags: FeatureFlags = env.features;

export const moduleFlags: ModuleFlags = {
  sandbox: featureFlags.sandbox,
  search: featureFlags.search,
  admin: featureFlags.admin,
};

// Helper function to check if a feature is enabled
export const isFeatureEnabled = (feature: keyof FeatureFlags): boolean => {
  return featureFlags[feature];
};

export const getRuntimeFlag = (feature: keyof FeatureFlags): boolean => {
  if (typeof window === 'undefined') {
    return featureFlags[feature];
  }

  const key = `goblin_flag:${String(feature)}`;
  const stored = window.localStorage.getItem(key);
  if (stored === null) {
    return featureFlags[feature];
  }

  return stored === 'true' || stored === '1';
};

const hashExperimentKey = (input: string): number => {
  let hash = 0;
  for (let i = 0; i < input.length; i += 1) {
    hash = (hash * 31 + input.charCodeAt(i)) >>> 0;
  }
  return hash;
};

export const getExperimentVariant = (
  experiment: Experiment,
  userId: string,
): ExperimentVariant => {
  if (experiment.variants.length === 0) {
    return 'control';
  }

  const bucket = hashExperimentKey(`${experiment.name}:${userId}`) % experiment.variants.length;
  return experiment.variants[bucket] ?? experiment.variants[0] ?? 'control';
};

export const getEnabledModules = (): ModuleFlags => moduleFlags;

// Log enabled features in development
if (env.isDevelopment && featureFlags.debugMode) {
  devLog('🚩 Feature Flags:', featureFlags);
}
