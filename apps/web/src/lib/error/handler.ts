import { UiError } from '../ui-error';

export type ErrorSeverity = 'fatal' | 'error' | 'warning';

export interface AppError {
  code: string;
  userMessage: string;
  severity: ErrorSeverity;
  retryable: boolean;
  cause?: unknown | undefined;
}

/** HTTP status codes that are safe to retry automatically. */
const RETRYABLE_STATUSES = new Set([408, 429, 500, 502, 503, 504]);

/** HTTP status codes that should be classified as fatal (no retry, navigate away). */
const FATAL_STATUSES = new Set([401, 403]);

function getHttpStatus(error: unknown): number | null {
  if (error == null || typeof error !== 'object') return null;
  const e = error as Record<string, unknown>;
  const status =
    (e['status'] as number | undefined) ??
    ((e['response'] as Record<string, unknown> | undefined)?.['status'] as number | undefined);
  return typeof status === 'number' ? status : null;
}

/**
 * Converts any thrown value into a structured `AppError`.
 *
 * Precedence:
 *   1. `UiError` — already structured, preserved as-is.
 *   2. HTTP errors — classified by status code.
 *   3. Plain `Error` — message forwarded, generic code applied.
 *   4. Unknown — fully generic fallback.
 */
export function handleError(error: unknown, fallbackCode = 'UNKNOWN_ERROR'): AppError {
  if (error instanceof UiError) {
    return {
      code: error.code,
      userMessage: error.userMessage,
      severity: 'error',
      retryable: false,
      cause: error.cause,
    };
  }

  const status = getHttpStatus(error);

  if (status !== null) {
    if (FATAL_STATUSES.has(status)) {
      return {
        code: 'AUTH_ERROR',
        userMessage: 'You need to sign in to continue.',
        severity: 'fatal',
        retryable: false,
        cause: error,
      };
    }

    if (status === 404) {
      return {
        code: 'NOT_FOUND',
        userMessage: 'The requested resource was not found.',
        severity: 'error',
        retryable: false,
        cause: error,
      };
    }

    if (status === 422 || status === 400) {
      return {
        code: 'VALIDATION_ERROR',
        userMessage: 'The request was invalid. Please check your input and try again.',
        severity: 'warning',
        retryable: false,
        cause: error,
      };
    }

    if (RETRYABLE_STATUSES.has(status)) {
      return {
        code: `HTTP_${status}`,
        userMessage: 'A server error occurred. Please try again in a moment.',
        severity: 'error',
        retryable: true,
        cause: error,
      };
    }
  }

  const message =
    error instanceof Error
      ? error.message
      : typeof error === 'string'
        ? error
        : 'An unexpected error occurred.';

  return {
    code: fallbackCode,
    userMessage: message || 'An unexpected error occurred.',
    severity: 'error',
    retryable: false,
    cause: error,
  };
}

/** Returns true when the error is worth retrying automatically. */
export function isRetryable(error: unknown): boolean {
  return handleError(error).retryable;
}
