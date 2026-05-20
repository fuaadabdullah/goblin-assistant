/**
 * Debug utility for conditional logging based on environment
 */

import { devDebug, devError, devWarn } from '@/utils/dev-log';

const isDebugEnabled = (): boolean =>
  process.env.NEXT_PUBLIC_DEBUG_MODE === 'true' || process.env.NODE_ENV === 'development';

export const debugLog = (...args: unknown[]): void => {
  if (isDebugEnabled()) {
    devDebug(...args);
  }
};

export const debugWarn = (...args: unknown[]): void => {
  if (isDebugEnabled()) {
    devWarn(...args);
  }
};

export const debugError = (...args: unknown[]): void => {
  if (isDebugEnabled()) {
    devError(...args);
  }
};

/**
 * Create a prefixed debug logger for a specific module
 */
export const createDebugLogger = (prefix: string) => ({
  log: (...args: unknown[]) => debugLog(`[${prefix}]`, ...args),
  warn: (...args: unknown[]) => debugWarn(`[${prefix}]`, ...args),
  error: (...args: unknown[]) => debugError(`[${prefix}]`, ...args),
});
