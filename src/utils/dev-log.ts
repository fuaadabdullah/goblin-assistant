/**
 * Development-only logging utility
 * Console logs are automatically removed in production builds
 */

import { env } from '../config/env';

/**
 * Log only in development environment.
 * No-op in production builds.
 */
export function devLog(...args: unknown[]): void {
  if (env.isDevelopment) {
    // eslint-disable-next-line no-console
    console.log(...args);
  }
}

/**
 * Log warnings only in development.
 * Fully suppressed in production — use monitoring.ts for production error tracking.
 */
export function devWarn(...args: unknown[]): void {
  if (env.isDevelopment) {
    // eslint-disable-next-line no-console
    console.warn(...args);
  }
}

/**
 * Log errors in all environments.
 * Consider using logErrorToService() from monitoring.ts for production errors.
 */
export function devError(...args: unknown[]): void {
  // eslint-disable-next-line no-console
  console.error(...args);
}
