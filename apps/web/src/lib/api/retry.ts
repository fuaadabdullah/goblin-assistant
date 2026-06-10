/**
 * Retry Logic
 *
 * Exponential-backoff retry wrapper for transient API failures.
 * Extracted from the former shared.ts modularization.
 */

import { devWarn } from '../../utils/dev-log';

/**
 * Retry wrapper for transient failures (5xx, timeouts, network errors).
 * Exponential backoff with jitter to prevent thundering herd.
 */
export const withTransientRetry = async <T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelayMs: number = 100
): Promise<T> => {
  let lastError: unknown;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      // Determine if error is transient
      type ErrorWithStatus = Error & { status?: unknown };
      const err = error as ErrorWithStatus;
      const isTransientStatus =
        error instanceof Error &&
        typeof err.status === 'number' &&
        (err.status >= 500 || err.status === 408);

      const isNetworkError =
        error instanceof Error &&
        (error.message.includes('timeout') ||
          error.message.includes('network') ||
          error.message.includes('ECONNABORTED'));

      const isRetryable = isTransientStatus || isNetworkError;

      // Don't retry on last attempt or non-transient errors
      if (!isRetryable || attempt === maxRetries - 1) {
        throw error;
      }

      // Exponential backoff with jitter
      const exponentialDelay = baseDelayMs * Math.pow(2, attempt);
      const jitter = exponentialDelay * (0.8 + Math.random() * 0.4);
      const delayMs = Math.min(jitter, 5000);

      devWarn(`Conversation API transient error, retrying in ${delayMs}ms`, {
        attempt: attempt + 1,
        maxRetries,
        error: error instanceof Error ? error.message : String(error),
      });

      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }

  throw lastError;
};