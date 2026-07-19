/**
 * HTTP Client
 *
 * Axios instances, auth interceptor, token refresh logic, and shared constants.
 * Extracted from the former shared.ts modularization.
 */

import axios, { AxiosError, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios';
export { V1_API_PREFIX } from '@goblin/shared';
import { env } from '../../config/env';
import {
  clearAuthSession,
  getAuthToken,
  getRefreshToken,
  persistAuthSession,
} from '../../utils/auth-session';

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

// The backend client is used by protected pages only, so attach its Supabase
// interceptor lazily from the auth bootstrapper.
let backendSupabaseInterceptorAttached = false;

const setAuthorizationHeader = (headers: InternalAxiosRequestConfig['headers'], token: string) => {
  headers['Authorization'] = `Bearer ${token}`;
};

const loadSupabaseAuthHelpers = async () => {
  const { authGetSession, authRefreshSession, supabaseConfigured } = await import('../supabase');
  return { authGetSession, authRefreshSession, supabaseConfigured };
};

const refreshAccessTokenViaBackend = async (
  refreshToken: string | null
): Promise<string | null> => {
  try {
    const response = await frontendHttp.post<{
      access_token: string;
      refresh_token?: string;
      expires_in?: number;
      user?: Record<string, unknown>;
    }>(`${INTERNAL_AUTH_PREFIX}/refresh`, {
      refresh_token: refreshToken ?? undefined,
    });

    const accessToken = response.data?.access_token ?? null;
    if (!accessToken) return null;

    persistAuthSession({
      token: accessToken,
      refreshToken: response.data?.refresh_token ?? refreshToken,
      user: response.data?.user,
      expiresIn: response.data?.expires_in,
    });

    return accessToken;
  } catch {
    clearAuthSession();
    return null;
  }
};

const refreshAccessTokenViaSupabase = async (): Promise<string | null> => {
  const { authGetSession, authRefreshSession, supabaseConfigured } =
    await loadSupabaseAuthHelpers();

  if (!supabaseConfigured) return null;

  const { session: existing } = await authGetSession();
  if (!existing) return null;

  const { session } = await authRefreshSession();
  return session?.access_token ?? null;
};

const attachSupabaseRequestInterceptor = (client: typeof backendHttp): void => {
  client.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
    // Dynamic import keeps Supabase out of public-route bundles until an API
    // request actually needs it.
    const { authGetSession } = await import('../supabase');
    const { session } = await authGetSession();

    // Keep the freshly refreshed token when a 401 request is retried.
    if (session?.access_token && !(config as RetryableRequestConfig)._retry) {
      setAuthorizationHeader(config.headers, session.access_token);
    }
    return config;
  });
};

export async function attachSupabaseInterceptor() {
  if (backendSupabaseInterceptorAttached) return;
  backendSupabaseInterceptorAttached = true;
  attachSupabaseRequestInterceptor(backendHttp);
}

export const frontendHttp = axios.create({
  timeout: 45000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Chat uses this client before React effects necessarily run. Attach its lazy
// token lookup at module initialization so the first conversation request is
// authenticated as well.
attachSupabaseRequestInterceptor(frontendHttp);

// ============================================================================
// Auth & Token Refresh
// ============================================================================

type RetryableRequestConfig = AxiosRequestConfig & { _retry?: boolean };

let refreshPromise: Promise<string | null> | null = null;

export const refreshAccessToken = async (): Promise<string | null> => {
  // Supabase sessions refresh through the Supabase client, not the legacy
  // backend endpoint — hitting /auth/refresh with no legacy session would
  // fail and wipe the auth cookies mid-session.
  const supabaseToken = await refreshAccessTokenViaSupabase();
  if (supabaseToken) return supabaseToken;

  return refreshAccessTokenViaBackend(getRefreshToken());
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
