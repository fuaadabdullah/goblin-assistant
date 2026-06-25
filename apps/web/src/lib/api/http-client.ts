/**
 * HTTP Client
 *
 * Axios instances, auth interceptor, token refresh logic, and shared constants.
 * Extracted from the former shared.ts modularization.
 */

import axios, { AxiosError, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios';
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
export const V1_API_PREFIX = '/api/v1';
export const V1_CHAT_PREFIX = `${V1_API_PREFIX}/chat`;

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

const setAuthorizationHeader = (
  headers: InternalAxiosRequestConfig['headers'],
  token: string
) => {
  headers['Authorization'] = `Bearer ${token}`;
};

const loadSupabaseAuthHelpers = async () => {
  const { authGetSession, authRefreshSession, supabaseConfigured } = await import('../supabase');
  return { authGetSession, authRefreshSession, supabaseConfigured };
};

const refreshAccessTokenViaBackend = async (refreshToken: string | null): Promise<string | null> => {
  try {
    const response = await backendHttp.post<{
      access_token: string;
      refresh_token?: string;
      expires_in?: number;
      user?: Record<string, unknown>;
    }>(`${V1_API_PREFIX}/auth/refresh`, {
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
  const { authGetSession, authRefreshSession, supabaseConfigured } = await loadSupabaseAuthHelpers();

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

  // Attach Supabase access token as Bearer before every backend request.
  // Supabase auto-refreshes tokens; getSession() is a fast local read.
  backendHttp.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
    const { session } = await authGetSession();
    if (session?.access_token) {
      setAuthorizationHeader(config.headers, session.access_token);
    }
    return config;
  });
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

export const refreshAccessToken = async (): Promise<string | null> => {
  // Supabase sessions refresh through the Supabase client, not the legacy
  // backend endpoint — hitting /auth/refresh with no legacy session would
  // fail and wipe the auth cookies mid-session.
  const supabaseToken = await refreshAccessTokenViaSupabase();
  if (supabaseToken) return supabaseToken;

  return refreshAccessTokenViaBackend(getRefreshToken());
};

backendHttp.interceptors.response.use(
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

    return backendHttp(originalRequest);
  }
);

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
