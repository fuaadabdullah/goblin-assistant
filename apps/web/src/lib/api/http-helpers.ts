/**
 * HTTP Helpers
 *
 * Typed HTTP verb wrappers (getBackend, postBackend, etc.), error handling
 * utilities, and the StandardApiEnvelope unwrapper.
 * Extracted from the former shared.ts modularization.
 */

import axios, { AxiosError, type AxiosRequestConfig } from 'axios';
import { devWarn } from '../../utils/dev-log';
import { getAuthTokenForRequest } from '../../utils/auth-session';
import { backendHttp, frontendHttp } from './http-client';
import type { StandardApiEnvelope } from './api-types';

// ============================================================================
// Error Handling
// ============================================================================

export const extractApiErrorMessage = (payload: unknown, fallback = 'Request failed'): string => {
  if (!payload || typeof payload !== 'object') return fallback;

  const data = payload as Record<string, unknown>;
  const envelopeError = data['error'];
  if (envelopeError && typeof envelopeError === 'object') {
    const message = (envelopeError as Record<string, unknown>)['message'];
    if (typeof message === 'string' && message.trim()) return message;
  }
  if (typeof data['message'] === 'string' && data['message'].trim()) return data['message'];
  if (typeof data['detail'] === 'string' && data['detail'].trim()) return data['detail'];
  if (typeof envelopeError === 'string' && envelopeError.trim()) return envelopeError;
  return fallback;
};

export const normalizeAxiosError = (error: unknown): never => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<Record<string, unknown>>;
    const payload = axiosError.response?.data;

    const isTimeout = axiosError.code === 'ECONNABORTED';

    const detail =
      (isTimeout &&
        'Authentication service timed out. The server may be waking up—please try again in a few seconds.') ||
      extractApiErrorMessage(payload, '') ||
      axiosError.message ||
      'Request failed';

    const normalizedError = new Error(detail) as Error & {
      status?: number | undefined;
      responseData?: Record<string, unknown> | undefined;
    };
    normalizedError.status = axiosError.response?.status;
    normalizedError.responseData = payload;

    throw normalizedError;
  }

  throw error instanceof Error ? error : new Error('Request failed');
};

export const unwrapEnvelope = <T>(payload: T | StandardApiEnvelope<T>): T => {
  if (typeof payload !== 'object' || payload === null) return payload as T;
  if (!('success' in payload)) return payload as T;

  const envelope = payload as StandardApiEnvelope<T>;
  if (envelope.success && envelope.data !== undefined) {
    return envelope.data;
  }
  return payload as T;
};

// ============================================================================
// Versioned path guard
// ============================================================================

// Reject the removed legacy prefix before it reaches the production backend.
const LEGACY_V1_PATH_PATTERN = /^\/?v1(\/|$)/i;

export const assertNoVersionedClientPath = (path: string): void => {
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return;
  }

  if (LEGACY_V1_PATH_PATTERN.test(path.trim())) {
    throw new Error(
      `Refusing API path "${path}". Frontend clients must use internal routes, not provider-style /v1 endpoints.`
    );
  }
};

const isAuthRoute = (url: string): boolean =>
  url.split('?', 1)[0]?.startsWith('/api/auth/') ?? false;

/**
 * Resolve the current browser session at request time.
 *
 * Supabase owns the active session, while several older callers still pass
 * synchronous `withAuth()` config built from legacy storage. Resolving here
 * keeps chat, account, and settings requests authenticated even when the
 * lazy interceptor has not attached yet, and replaces stale legacy headers
 * when a current Supabase session is available.
 */
const withResolvedAuth = async (url: string, config?: AxiosRequestConfig) => {
  if (isAuthRoute(url)) return config;

  const token = await getAuthTokenForRequest();
  if (!token) return config;

  return {
    ...config,
    headers: {
      ...(config?.headers ?? {}),
      Authorization: `Bearer ${token}`,
    },
  };
};

// ============================================================================
// HTTP Verb Wrappers — Backend
// ============================================================================

export const getBackend = async <T>(url: string, config?: AxiosRequestConfig): Promise<T> => {
  try {
    assertNoVersionedClientPath(url);
    const response = await backendHttp.get<T>(url, await withResolvedAuth(url, config));
    return unwrapEnvelope<T>(response.data as T | StandardApiEnvelope<T>);
  } catch (error) {
    return normalizeAxiosError(error);
  }
};

export const postBackend = async <T, B = unknown>(
  url: string,
  body?: B,
  config?: AxiosRequestConfig
): Promise<T> => {
  try {
    assertNoVersionedClientPath(url);
    const response = await backendHttp.post<T>(url, body, await withResolvedAuth(url, config));
    return unwrapEnvelope<T>(response.data as T | StandardApiEnvelope<T>);
  } catch (error) {
    return normalizeAxiosError(error);
  }
};

export const putBackend = async <T, B = unknown>(
  url: string,
  body?: B,
  config?: AxiosRequestConfig
): Promise<T> => {
  try {
    assertNoVersionedClientPath(url);
    const response = await backendHttp.put<T>(url, body, await withResolvedAuth(url, config));
    return unwrapEnvelope<T>(response.data as T | StandardApiEnvelope<T>);
  } catch (error) {
    return normalizeAxiosError(error);
  }
};

export const patchBackend = async <T, B = unknown>(
  url: string,
  body?: B,
  config?: AxiosRequestConfig
): Promise<T> => {
  try {
    assertNoVersionedClientPath(url);
    const response = await backendHttp.patch<T>(url, body, await withResolvedAuth(url, config));
    return unwrapEnvelope<T>(response.data as T | StandardApiEnvelope<T>);
  } catch (error) {
    return normalizeAxiosError(error);
  }
};

export const deleteBackend = async <T>(url: string, config?: AxiosRequestConfig): Promise<T> => {
  try {
    assertNoVersionedClientPath(url);
    const response = await backendHttp.delete<T>(url, await withResolvedAuth(url, config));
    return unwrapEnvelope<T>(response.data as T | StandardApiEnvelope<T>);
  } catch (error) {
    return normalizeAxiosError(error);
  }
};

// ============================================================================
// HTTP Verb Wrappers — Frontend (Next.js proxy)
// ============================================================================

export const getFrontend = async <T>(url: string, config?: AxiosRequestConfig): Promise<T> => {
  try {
    assertNoVersionedClientPath(url);
    const response = await frontendHttp.get<T>(url, await withResolvedAuth(url, config));
    return unwrapEnvelope<T>(response.data as T | StandardApiEnvelope<T>);
  } catch (error) {
    return normalizeAxiosError(error);
  }
};

export const postFrontend = async <T, B = unknown>(
  url: string,
  body?: B,
  config?: AxiosRequestConfig
): Promise<T> => {
  try {
    assertNoVersionedClientPath(url);
    const response = await frontendHttp.post<T>(url, body, await withResolvedAuth(url, config));
    return unwrapEnvelope<T>(response.data as T | StandardApiEnvelope<T>);
  } catch (error) {
    return normalizeAxiosError(error);
  }
};

export const putFrontend = async <T, B = unknown>(
  url: string,
  body?: B,
  config?: AxiosRequestConfig
): Promise<T> => {
  try {
    assertNoVersionedClientPath(url);
    const response = await frontendHttp.put<T>(url, body, await withResolvedAuth(url, config));
    return unwrapEnvelope<T>(response.data as T | StandardApiEnvelope<T>);
  } catch (error) {
    return normalizeAxiosError(error);
  }
};

export const patchFrontend = async <T, B = unknown>(
  url: string,
  body?: B,
  config?: AxiosRequestConfig
): Promise<T> => {
  try {
    assertNoVersionedClientPath(url);
    const response = await frontendHttp.patch<T>(url, body, await withResolvedAuth(url, config));
    return unwrapEnvelope<T>(response.data as T | StandardApiEnvelope<T>);
  } catch (error) {
    return normalizeAxiosError(error);
  }
};

export { devWarn };
