/**
 * Debug utility for conditional logging based on environment
 */

const isDebugEnabled =
  process.env.NEXT_PUBLIC_DEBUG_MODE === 'true' || process.env.NODE_ENV === 'development';

export const debugLog = (...args: unknown[]): void => {
  if (isDebugEnabled) {
    console.debug(...args);
  }
};

export const debugWarn = (...args: unknown[]): void => {
  if (isDebugEnabled) {
    console.warn(...args);
  }
};

export const debugError = (...args: unknown[]): void => {
  if (isDebugEnabled) {
    console.error(...args);
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
