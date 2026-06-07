/**
 * Development-only logging utility
 * Only console.warn and console.error are permitted.
 * console.warn calls are stripped in production builds via next.config.ts compiler.removeConsole.
 * console.error calls are kept for production error reporting.
 */

const shouldLog = (): boolean => process.env['NODE_ENV'] !== 'production';

/**
 * Log warnings only in development.
 * Fully suppressed in production — use monitoring.ts for production error tracking.
 */
export function devWarn(...args: unknown[]): void {
  if (!shouldLog()) {
    return;
  }

  console.warn(...args);
}

/**
 * Log errors only outside production.
 * Consider using logErrorToService() from monitoring.ts for production errors.
 */
export function devError(...args: unknown[]): void {
  if (!shouldLog()) {
    return;
  }

  console.error(...args);
}