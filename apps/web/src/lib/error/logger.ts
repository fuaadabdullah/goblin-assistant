import { handleError, type AppError } from './handler';

export interface ErrorContext {
  component?: string | undefined;
  action?: string | undefined;
  userId?: string | undefined;
  [key: string]: unknown;
}

/**
 * Structured error logger.
 *
 * In development, writes a formatted group to the console.
 * In production, forwards to Datadog RUM (if the agent is loaded) and
 * preserves a `console.error` call so the error still appears in logs.
 *
 * All errors are converted to `AppError` before logging so the shape is
 * always consistent regardless of the throw site.
 */
export function logError(error: unknown, context: ErrorContext = {}): AppError {
  const appError = handleError(error);

  if (typeof window === 'undefined') {
    // Server-side: plain console.error for log aggregation
    console.error('[error]', appError.code, appError.userMessage, context, appError.cause);
    return appError;
  }

  if (process.env['NODE_ENV'] === 'development') {
    console.error(
      `[error] ${appError.code} — ${appError.userMessage}`,
      { severity: appError.severity, retryable: appError.retryable, context },
      appError.cause
    );
  } else {
    console.error(`[error] ${appError.code}: ${appError.userMessage}`, context);

    // Forward to Datadog RUM when available
    const dd = (window as unknown as Record<string, unknown>)['DD_RUM'] as
      | { addError?: (err: unknown, ctx?: unknown) => void }
      | undefined;
    if (typeof dd?.addError === 'function') {
      dd.addError(appError.cause ?? error, { ...context, appErrorCode: appError.code });
    }
  }

  return appError;
}
