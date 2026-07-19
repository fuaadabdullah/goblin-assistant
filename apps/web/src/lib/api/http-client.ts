/**
 * HTTP Client
 *
 * Axios instances, auth interceptor, token refresh logic, and shared constants.
 * Extracted from the former shared.ts modularization.
 */

import axios, {
  type AxiosError,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios';
export { V1_API_PREFIX } from '@goblin/shared';
import { env } from '../../config/env';
import { getAuthToken } from '../../utils/auth-session';

// ============================================================================
// Constants
// ============================================================================

export const AUTH_REQUEST_TIMEOUT_MS = 60000;
const INTERNAL_AUTH_PREFIX = '/api/auth';

// ============================================================================
// Axios Instances
// ============================================================================

export const backendHttp = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: 45000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Lazy-load Supabase to avoid bloating public routes. Attached only on first request.
let supabaseInterceptorAttached = false;

const setAuthorizationHeader = (headers: InternalAxiosRequestConfig['headers'], token: string) => {
  headers['Authorization'] = `Bearer ${token}`;
};

const loadSupabaseAuthHelpers = async () => {
  const { authGetSession, authRefreshSession, supabaseConfigured } = await import('../supabase');
  return { authGetSession, authRefreshSession, supabaseConfigured };
};

export const refreshAccessTokenViaSupabase = async (): Promise<string | null> => {
  const { authGetSession, authRefreshSession, supabaseConfigured } =
    await loadSupabaseAuthHelpers();

  if (!supabaseConfigured) return null;

  const { session: existing } = await authGetSession();
  if (!existing) return null;

  const { session } = await authRefreshSession();
  return session?.access_token ?? null;
};

export async function attachSupabaseInterceptor() {
  if (supabaseInterceptorAttached) return;
  supabaseInterceptorAttached = true;

  // Dynamic import to keep supabase out of public route bundles.
  const { authGetSession } = await import('../supabase');

  const attachAuthInterceptor = (client: typeof backendHttp) => {
    client.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
      const { session } = await authGetSession();
      // A response interceptor may have just refreshed the token after a 401.
      // Preserve that explicit retry token instead of replacing it with the
      // stale value returned by the initial session lookup.
      if (session?.access_token && !(config as RetryableRequestConfig)._retry) {
        setAuthorizationHeader(config.headers, session.access_token);
      }
      return config;
    });
  };

  // The frontend client talks to the same backend through the Next.js proxy,
  // so it must carry the Supabase Bearer token just like direct backend calls.
  attachAuthInterceptor(backendHttp);
  attachAuthInterceptor(frontendHttp);
}

export const frontendHttp = axios.create({
  timeout: 45000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================================================
// Auth & Token Refresh
// ============================================================================

type RetryableRequestConfig = AxiosRequestConfig & { _retry?: boolean };

let refreshPromise: Promise<string | null> | null = null;

/**
 * Refresh the access token using Supabase.
 *
 * Per ADR-0006, authentication is Supabase-only. The legacy backend refresh
 * endpoint has been removed to consolidate on a single auth source of truth.
 */
export const refreshAccessToken = async (): Promise<string | null> => {
  return refreshAccessTokenViaSupabase();
};

const attachAccessTokenRefreshInterceptor = (client: typeof backendHttp): void => {
  client.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const originalRequest = (error.config ?? {}) as RetryableRequestConfig;
      const status = error.response?.status;
      const requestUrl = String(originalRequest.url ?? '');

      // Never retry auth endpoints — a 401 on login/register/passkey is a real credential failure,
      // not an expired session. Retrying with a refreshed token would silently swallow the error.
      const isAuthEndpoint = requestUrl.includes('/auth/');
      const canRetry = status === 401 && !originalRequest._retry && !isAuthEndpoint;

      if (!canRetry) {
        return Promise.reject(error);
      }

      originalRequest._retry = true;

      if (!refreshPromise) {
        refreshPromise = refreshAccessToken().finally(() => {
          refreshPromise = null;
        });
      }

      const nextToken = await refreshPromise;
      if (!nextToken) {
        return Promise.reject(error);
      }

      originalRequest.headers = {
        ...(originalRequest.headers ?? {}),
        Authorization: `Bearer ${nextToken}`,
      };

      return client(originalRequest);
    }
  );
};

// Both clients ultimately call the same authenticated backend. Requests made
// through the Next.js proxy used to bypass this recovery path, leaving an
// expired Supabase access token as a permanent 401 for chat creation.
attachAccessTokenRefreshInterceptor(backendHttp);
attachAccessTokenRefreshInterceptor(frontendHttp);

export const withAuth = (config?: AxiosRequestConfig): AxiosRequestConfig => {
  const token = getAuthToken();
  if (!token) return config ?? {};

  return {
    ...config,
    headers: {
      ...(config?.headers ?? {}),
      Authorization: `Bearer ${token}`,
    },
  };
};
