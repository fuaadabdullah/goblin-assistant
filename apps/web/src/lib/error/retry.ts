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

      const isLast = attempt === maxAttempts;
      if (isLast || !shouldRetry(error)) throw error;

      const continueRetry = onRetry?.(attempt, error);
      if (continueRetry === false) throw error;

      const jitter = Math.random() * 200;
      const backoff = Math.min(baseDelayMs * 2 ** (attempt - 1) + jitter, maxDelayMs);
      await delay(backoff);
    }
  }

  throw lastError;
}
