'use client';

import { useSyncExternalStore } from 'react';
import {
  getRuntimeFlag,
  featureFlags,
  type FeatureFlags,
} from '../config/features';

function subscribe(callback: () => void): () => void {
  window.addEventListener('storage', callback);
  return () => window.removeEventListener('storage', callback);
}

/**
 * Reactive feature flag hook.
 *
 * Returns the runtime value (env default + any localStorage override).
 * Re-renders automatically when a flag override is changed in another tab via
 * the `storage` event.
 *
 * Usage:
 *   const isEnabled = useFeatureFlag('ragEnabled');
 */
export function useFeatureFlag(feature: keyof FeatureFlags): boolean {
  return useSyncExternalStore(
    subscribe,
    () => getRuntimeFlag(feature),
    () => featureFlags[feature],
  );
}
