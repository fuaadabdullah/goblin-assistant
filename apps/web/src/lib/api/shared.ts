import axios, { AxiosError, type AxiosRequestConfig } from 'axios';
import { env } from '../../config/env';
import { devWarn } from '../../utils/dev-log';
import {
  clearAuthSession,
  getAuthToken,
  getRefreshToken,
  persistAuthSession,
} from '../../utils/auth-session';
import type { ChatMessage as DomainChatMessage, ChatUsage } from '../../domain/chat';
import type {
  ChatMessage,
  ChatCompletionResponse,
  HealthStatus,
  ValidateTokenResponse,
} from '../../types/api';

// ============================================================================
// Type Exports
// ============================================================================

export interface ProviderUpdatePayload {
  name?: string;
  enabled?: boolean;
  priority?: number;
  weight?: number;
  api_key?: string;
  base_url?: string;
  models?: string[];
}

export interface PasskeyCredential {
  id: string;
  rawId: string;
  type: string;
  response: {
    attestationObject?: string;
    clientDataJSON: string;
    authenticatorData?: string;
    signature?: string;
  };
}

export interface SandboxRunPayload {
  code: string;
  language?: string;
  timeout?: number;
}

export interface AccountProfile {
  name?: string;
  email?: string;
  avatar_url?: string;
}

export interface AccountPreferences {
  theme?: string;
  default_model?: string;
  default_provider?: string;
  [key: string]: string | boolean | number | undefined;
}

export interface ConversationCreateResponse {
  conversation_id: string;
  title: string;
  created_at: string;
}

export interface ConversationInfoResponse {
  conversation_id: string;
  user_id?: string | null;
  title: string;
  message_count: number;
  snippet?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetailResponse {
  conversation_id: string;
  user_id?: string | null;
  title: string;
  messages: Array<{
    message_id: string;
    role: DomainChatMessage['role'];
    content: string;
    timestamp: string;
    metadata?: DomainChatMessage['meta'];
  }>;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, unknown>;
}

export interface ConversationSendResponse {
  message_id: string;
  response: string;
  provider: string;
  model: string;
  timestamp: string;
  usage?: ChatUsage;
  cost_usd?: number;
  correlation_id?: string;
  visualizations?: Array<{
    type: string;
    title: string;
    data: Record<string, unknown>[];
    config: Record<string, unknown>;
  }>;
}

export interface StandardApiErrorPayload {
  code?: string;
  type?: string;
  message?: string;
  request_id?: string;
  timestamp?: string;
  trace_id?: string;
  details?: Record<string, unknown>;
}

export interface StandardApiEnvelope<T> {
  success: boolean;
  data?: T;
  error?: StandardApiErrorPayload | string;
}

// ============================================================================
// Axios Configuration
// ============================================================================

export const backendHttp = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: 45000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const frontendHttp = axios.create({
  timeout: 45000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================================================
// Constants
// ============================================================================

export const AUTH_REQUEST_TIMEOUT_MS = 60000;
export const V1_API_PREFIX = '/v1';
export const V1_CHAT_PREFIX = '/v1/chat';

type RetryableRequestConfig = AxiosRequestConfig & { _retry?: boolean };

let refreshPromise: Promise<string | null> | null = null;

// ============================================================================
// Auth & Middleware
// ============================================================================

export const refreshAccessToken = async (): Promise<string | null> => {
  const refreshToken = getRefreshToken();

  try {
    const response = await backendHttp.post<{
      access_token: string;
      refresh_token?: string;
      expires_in?: number;
      user?: Record<string, unknown>;
    }>(`/auth/refresh`, {
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

// ============================================================================
// Error Handling
// ============================================================================

export const extractApiErrorMessage = (payload: unknown, fallback = 'Request failed'): string => {
  if (!payload || typeof payload !== 'object') return fallback;

  const data = payload as Record<string, unknown>;
  const envelopeError = data.error;
  if (envelopeError && typeof envelopeError === 'object') {
    const message = (envelopeError as Record<string, unknown>).message;
    if (typeof message === 'string' && message.trim()) return message;
  }
  if (typeof envelopeError === 'string' && envelopeError.trim()) return envelopeError;
  if (typeof data.message === 'string' && data.message.trim()) return data.message;
  if (typeof data.detail === 'string' && data.detail.trim()) return data.detail;
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
      status?: number;
      responseData?: Record<string, unknown>;
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
// HTTP Helpers (private, used within this module)
// ============================================================================

// Matches /v1/... but not /v1/auth/... — backend auth routes legitimately live at /v1/auth/.
const V1_PATH_PATTERN = /^\/?v1(?!\/auth)(\/|$)/i;

const assertNoVersionedClientPath = (path: string): void => {
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return;
  }

  if (V1_PATH_PATTERN.test(path.trim())) {
    throw new Error(
      `Refusing API path "${path}". Frontend clients must use internal routes, not provider-style /v1 endpoints.`
    );
  }
};

export const getBackend = async <T>(url: string, config?: AxiosRequestConfig): Promise<T> => {
  try {
    assertNoVersionedClientPath(url);
    const response = await backendHttp.get<T>(url, config);
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
    const response = await backendHttp.post<T>(url, body, config);
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
    const response = await backendHttp.put<T>(url, body, config);
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
    const response = await backendHttp.patch<T>(url, body, config);
    return unwrapEnvelope<T>(response.data as T | StandardApiEnvelope<T>);
  } catch (error) {
    return normalizeAxiosError(error);
  }
};

export const deleteBackend = async <T>(url: string, config?: AxiosRequestConfig): Promise<T> => {
  try {
    assertNoVersionedClientPath(url);
    const response = await backendHttp.delete<T>(url, config);
    return unwrapEnvelope<T>(response.data as T | StandardApiEnvelope<T>);
  } catch (error) {
    return normalizeAxiosError(error);
  }
};

export const getFrontend = async <T>(url: string, config?: AxiosRequestConfig): Promise<T> => {
  try {
    assertNoVersionedClientPath(url);
    const response = await frontendHttp.get<T>(url, config);
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
    const response = await frontendHttp.post<T>(url, body, config);
    return unwrapEnvelope<T>(response.data as T | StandardApiEnvelope<T>);
  } catch (error) {
    return normalizeAxiosError(error);
  }
};

// ============================================================================
// Retry Logic
// ============================================================================

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
      const isTransientStatus =
        error instanceof Error &&
        'status' in error &&
        typeof (error as any).status === 'number' &&
        ((error as any).status >= 500 || (error as any).status === 408);

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

// ============================================================================
// CSRF Token
// ============================================================================

export const getCsrfToken = async (): Promise<string> => {
  const response = await getBackend<{ csrf_token?: string }>(`/auth/csrf-token`, {
    timeout: AUTH_REQUEST_TIMEOUT_MS,
  });

  const token = response?.csrf_token;
  if (!token || typeof token !== 'string') {
    throw new Error('Unable to initialize authentication. Please try again.');
  }

  return token;
};

// Re-export types for convenience
export type {
  DomainChatMessage,
  ChatUsage,
  ChatMessage,
  ChatCompletionResponse,
  HealthStatus,
  ValidateTokenResponse,
};

// Re-export utilities so they can be imported from shared
export { devWarn };
