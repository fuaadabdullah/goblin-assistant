import { isRetryable } from './handler';

export interface RetryOptions {
  /** Maximum number of attempts (including the first). Default: 3. */
  maxAttempts?: number | undefined;
  /** Base delay in ms. Each retry doubles this. Default: 500. */
  baseDelayMs?: number | undefined;
  /** Hard cap on delay per attempt. Default: 10 000. */
  maxDelayMs?: number | undefined;
  /**
   * Called after each failed attempt (before the retry delay).
   * Returning `false` cancels remaining retries.
   */
  onRetry?: ((attempt: number, error: unknown) => boolean | void) | undefined;
  /** Override retryability check. Default: `isRetryable` from handler. */
  shouldRetry?: ((error: unknown) => boolean) | undefined;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function computeBackoffMs(baseDelayMs: number, attempt: number, maxDelayMs: number): number {
  const jitter = Math.random() * 200;
  return Math.min(baseDelayMs * 2 ** (attempt - 1) + jitter, maxDelayMs);
}

function shouldAbortRetry(
  attempt: number,
  maxAttempts: number,
  error: unknown,
  shouldRetry: (error: unknown) => boolean,
  onRetry: ((attempt: number, error: unknown) => boolean | void) | undefined
): boolean {
  if (attempt === maxAttempts) return true;
  if (!shouldRetry(error)) return true;
  const continueRetry = onRetry?.(attempt, error);
  return continueRetry === false;
}

/**
 * Calls `fn` up to `maxAttempts` times with exponential backoff.
 *
 * Only retries when the error is classified as retryable by the error handler
 * (or by the custom `shouldRetry` predicate).  Non-retryable errors (auth
 * failures, 404s, validation errors) are re-thrown immediately.
 *
 * Usage:
 *   const result = await withRetry(() => apiClient.sendMessage(params), {
 *     maxAttempts: 3,
 *     baseDelayMs: 500,
 *   });
 */
export async function withRetry<T>(fn: () => Promise<T>, opts: RetryOptions = {}): Promise<T> {
  const {
    maxAttempts = 3,
    baseDelayMs = 500,
    maxDelayMs = 10_000,
    onRetry,
    shouldRetry = isRetryable,
  } = opts;

  let lastError: unknown;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      if (shouldAbortRetry(attempt, maxAttempts, error, shouldRetry, onRetry)) throw error;

      const backoff = computeBackoffMs(baseDelayMs, attempt, maxDelayMs);
      await delay(backoff);
    }
  }

  throw lastError;
}
