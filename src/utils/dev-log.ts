/**
 * Development-only logging utility
 * Console logs are automatically removed in production builds
 */

const shouldLog = (): boolean => process.env.NODE_ENV !== 'production';

const invokeConsole = (
  method: 'log' | 'info' | 'warn' | 'error' | 'debug',
  args: unknown[],
): void => {
  if (!shouldLog()) {
    return;
  }

  // eslint-disable-next-line no-console
  console[method](...args);
};

/**
 * Log only in development environment.
 * No-op in production builds.
 */
export function devLog(...args: unknown[]): void {
  invokeConsole('log', args);
}

export function devInfo(...args: unknown[]): void {
  invokeConsole('info', args);
}

/**
 * Log warnings only in development.
 * Fully suppressed in production — use monitoring.ts for production error tracking.
 */
export function devWarn(...args: unknown[]): void {
  invokeConsole('warn', args);
}

/**
 * Log errors only outside production.
 * Consider using logErrorToService() from monitoring.ts for production errors.
 */
export function devError(...args: unknown[]): void {
  invokeConsole('error', args);
}

export function devDebug(...args: unknown[]): void {
  invokeConsole('debug', args);
}
