/**
 * CSRF Token
 *
 * Single-use CSRF token management for auth endpoints.
 * Extracted from the former shared.ts modularization.
 */

import { AUTH_REQUEST_TIMEOUT_MS, V1_API_PREFIX } from './http-client';
import { getBackend } from './http-helpers';

// Single in-flight promise so concurrent callers share one request.
// Token is consumed on first use so it cannot be replayed.
let _csrfPrefetch: Promise<string> | null = null;

const fetchCsrfTokenFromBackend = async (): Promise<string> => {
  const response = await getBackend<{ csrf_token?: string }>(`${V1_API_PREFIX}/auth/csrf-token`, {
    timeout: AUTH_REQUEST_TIMEOUT_MS,
  });
  const token = response?.csrf_token;
  if (!token || typeof token !== 'string') {
    throw new Error('Unable to initialize authentication. Please try again.');
  }
  return token;
};

/** Warm the CSRF token in the background so submit() has it ready. */
export const prefetchCsrfToken = (): void => {
  if (!_csrfPrefetch) {
    _csrfPrefetch = fetchCsrfTokenFromBackend().catch(() => {
      // Reset on failure so the next call tries again.
      _csrfPrefetch = null;
      return Promise.reject(new Error('Unable to initialize authentication. Please try again.'));
    });
  }
};

export const getCsrfToken = async (): Promise<string> => {
  const pending = _csrfPrefetch;
  // Consume the cached promise so it isn't reused for a second submission.
  _csrfPrefetch = null;
  if (pending) return pending;
  return fetchCsrfTokenFromBackend();
};