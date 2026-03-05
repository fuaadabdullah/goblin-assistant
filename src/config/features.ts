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

export const getEnabledModules = (): ModuleFlags => moduleFlags;

// Log enabled features in development
if (env.isDevelopment && featureFlags.debugMode) {
  devLog('🚩 Feature Flags:', featureFlags);
}
