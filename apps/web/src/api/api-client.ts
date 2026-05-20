import { env } from '@/config/env';
import { devDebug, devWarn } from '@/utils/dev-log';
import { apiClient } from '@/lib/api';
import { normalizeProviderId } from '@/lib/providers/normalizeProvider';
import type {
  CostSummary,
  GoblinStats,
  GoblinStatus,
  MemoryEntry,
  OrchestrationPlan,
  ProviderModelOption,
  RuntimeClient,
  StreamChunk,
  TaskResponse,
} from '@/types/api';

export type {
  ProviderUpdatePayload,
  PasskeyCredential,
  SandboxRunPayload,
  AccountProfile,
  AccountPreferences,
} from '@/lib/api';

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

interface HttpResponse<T> {
  data: T;
}

type ModelRegistryItem = {
  name?: string;
  provider?: string;
  health?: string;
  is_selectable?: boolean;
  health_reason?: string | null;
};

type ProviderRegistryItem = {
  id?: string;
  health?: string;
  configured?: boolean;
  is_selectable?: boolean;
  health_reason?: string | null;
};

type ModelRegistryResponse = {
  models?: ModelRegistryItem[];
  providers?: ProviderRegistryItem[];
};

const V1_PATH_PATTERN = /^\/?v1(\/|$)/i;

const assertNoVersionedClientPath = (path: string): void => {
  if (V1_PATH_PATTERN.test(path.trim())) {
    throw new Error(
      `Refusing client API path "${path}". Frontend must call internal routes, not provider-style /v1 endpoints.`,
    );
  }
};

const buildUrl = (path: string): string => {
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  assertNoVersionedClientPath(path);
  if (path.startsWith('/')) return `${env.apiBaseUrl}${path}`;
  return `${env.apiBaseUrl}/${path}`;
};

const createTimeoutSignal = (ms: number): AbortSignal | undefined => {
  if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
    return AbortSignal.timeout(ms);
  }
  return undefined;
};

/**
 * Retry logic for transient errors with exponential backoff + jitter
 * Retries on: 429 (rate limit), 503 (service unavailable), 504 (gateway timeout)
 * Uses exponential backoff with jitter to prevent thundering herd
 */
const isTransientError = (status?: number): boolean => {
  return status === 429 || status === 503 || status === 504;
};

const isNetworkError = (error: unknown): boolean => {
  if (!(error instanceof Error)) return false;
  const message = error.message.toLowerCase();
  return (
    message.includes('network') ||
    message.includes('timeout') ||
    message.includes('failed to fetch') ||
    message.includes('aborted')
  );
};

/**
 * Calculate backoff delay with exponential increase and random jitter
 * Prevents thundering herd problem during recovery
 */
const calculateBackoffDelay = (
  attempt: number,
  baseDelayMs: number = 100,
): number => {
  const exponentialDelay = baseDelayMs * Math.pow(2, attempt);
  // Add jitter: ±20% random variance
  const jitter =
    exponentialDelay * (0.8 + Math.random() * 0.4);
  // Cap at 10 seconds to avoid excessive waiting
  return Math.min(jitter, 10000);
};

const withRetry = async <T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelayMs: number = 100,
): Promise<T> => {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError =
        error instanceof Error
          ? error
          : new Error(String(error));

      // Determine if error is retryable
      const isStatusTransient =
        typeof error === 'object' &&
        error !== null &&
        'status' in error &&
        isTransientError((error as { status?: number }).status);

      const isNetworkErr = isNetworkError(error);
      const isRetryable = isStatusTransient || isNetworkErr;

      // Don't retry on last attempt or non-transient errors
      if (!isRetryable || attempt === maxRetries - 1) {
        throw error;
      }

      // Calculate backoff with jitter
      const delayMs = calculateBackoffDelay(attempt, baseDelayMs);

      // Log retry attempt for debugging
      devDebug(
        `Request retry attempt ${attempt + 1}/${maxRetries}`,
        {
          error: lastError.message,
          delayMs,
          isStatusTransient,
          isNetworkErr,
        },
      );

      await new Promise(resolve =>
        setTimeout(resolve, delayMs),
      );
    }
  }

  throw (
    lastError || new Error('Request failed after retries')
  );
};

const request = async <T>(
  method: HttpMethod,
  path: string,
  body?: unknown,
): Promise<HttpResponse<T>> => {
  return withRetry(async () => {
    const requestStartTime = Date.now();

    const response = await fetch(buildUrl(path), {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body:
        body === undefined ? undefined : JSON.stringify(body),
      signal: createTimeoutSignal(30000), // 30s timeout where supported
    });

    const requestDuration = Date.now() - requestStartTime;

    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      let serverError: string | null = null;

      try {
        const payload = (await response.json()) as {
          detail?: string;
          error?: string;
        };
        detail = payload.detail || payload.error || detail;
        serverError = payload.error || payload.detail || null;
      } catch {
        // Keep the default message if the body is not JSON.
      }

      // Log failed requests with structured context
      devWarn(`API Error: ${method} ${path}`, {
        status: response.status,
        detail,
        durationMs: requestDuration,
        serverError,
        timestamp: new Date().toISOString(),
      });

      const error = new Error(detail) as Error & {
        status: number;
      };
      error.status = response.status;
      throw error;
    }

    // Log slow requests (>500ms)
    if (requestDuration > 500) {
      devDebug(`Slow API request: ${method} ${path}`, {
        durationMs: requestDuration,
      });
    }

    if (response.status === 204) {
      return { data: undefined as T };
    }

    const data = (await response.json()) as T;
    return { data };
  });
};

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T = unknown>(path: string, body?: unknown) => request<T>('POST', path, body),
  put: <T = unknown>(path: string, body?: unknown) => request<T>('PUT', path, body),
  patch: <T = unknown>(path: string, body?: unknown) => request<T>('PATCH', path, body),
  delete: <T = unknown>(path: string) => request<T>('DELETE', path),
};

const keyPrefix = 'goblin_provider_key:';

const storeKey = (provider: string) => `${keyPrefix}${provider}`;

async function loadModelRegistry(): Promise<ModelRegistryResponse> {
  const startTime = Date.now();
  try {
    const response = await fetch('/api/models', {
      method: 'GET',
      signal: createTimeoutSignal(10000), // 10s timeout where supported
    });

    const duration = Date.now() - startTime;

    if (!response.ok) {
      devWarn(
        `Model registry fetch failed: HTTP ${response.status}`,
        { durationMs: duration },
      );
      return { models: [], providers: [] };
    }

    const payload = (await response.json()) as ModelRegistryResponse;

    // Validate response structure
    const models = Array.isArray(payload?.models)
      ? payload.models
      : [];
    const providers = Array.isArray(payload?.providers)
      ? payload.providers
      : [];

    if (duration > 3000) {
      devDebug('Slow model registry load', {
        durationMs: duration,
        modelCount: models.length,
        providerCount: providers.length,
      });
    }

    return { models, providers };
  } catch (e) {
    const duration = Date.now() - startTime;
    const isTimeoutError =
      e instanceof Error && e.message.includes('timeout');

    // Log the error for observability
    devWarn('Failed to load model registry', {
      error:
        e instanceof Error ? e.message : String(e),
      type: e instanceof Error ? e.constructor.name : typeof e,
      isTimeoutError,
      durationMs: duration,
    });

    return { models: [], providers: [] };
  }
}

const normalizeHealth = (value: unknown): string => {
  const normalized = typeof value === 'string' ? value.trim().toLowerCase() : '';
  return normalized || 'unknown';
};

const isSelectableFlag = (value: unknown): boolean => value !== false;

const safeLocalStorage = {
  get(key: string): string | null {
    if (typeof window === 'undefined') return null;
    try {
      const value = window.localStorage.getItem(key);
      return value;
    } catch (e) {
      devWarn(
        `localStorage.getItem failed for key "${key}"`,
        {
          error:
            e instanceof Error ? e.message : String(e),
          type: typeof e,
        },
      );
      return null;
    }
  },
  set(key: string, value: string): void {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(key, value);
    } catch (e) {
      devWarn(
        `localStorage.setItem failed for key "${key}"`,
        {
          error:
            e instanceof Error ? e.message : String(e),
          type: typeof e,
          // Check if it's a quota error
          isQuotaError:
            e instanceof Error &&
            e.name === 'QuotaExceededError',
        },
      );
    }
  },
  remove(key: string): void {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.removeItem(key);
    } catch (e) {
      devWarn(
        `localStorage.removeItem failed for key "${key}"`,
        {
          error:
            e instanceof Error ? e.message : String(e),
          type: typeof e,
        },
      );
    }
  },
};

const emptyCostSummary: CostSummary = {
  total_cost: 0,
  cost_by_provider: {},
  cost_by_model: {},
  requests_by_provider: {},
};

const emptyOrchestration: OrchestrationPlan = {
  steps: [],
  total_batches: 0,
  max_parallel: 0,
};

const runtimeClientImpl: RuntimeClient = {
  async getGoblins(): Promise<GoblinStatus[]> {
    return [];
  },

  async getProviders(): Promise<string[]> {
    const registry = await loadModelRegistry();
    const seen = new Set<string>();
    const providers: string[] = [];

    for (const providerEntry of registry.providers || []) {
      const provider = normalizeProviderId(
        typeof providerEntry?.id === 'string' ? providerEntry.id : '',
      );
      if (!provider || seen.has(provider)) {
        continue;
      }
      seen.add(provider);
      providers.push(provider);
    }

    if (providers.length > 0) {
      return providers;
    }

    for (const item of registry.models || []) {
      const provider = normalizeProviderId(
        typeof item?.provider === 'string' ? item.provider : '',
      );
      if (!provider || seen.has(provider)) {
        continue;
      }
      seen.add(provider);
      providers.push(provider);
    }

    return providers;
  },

  async getProviderModelOptions(provider: string): Promise<ProviderModelOption[]> {
    const targetProvider = normalizeProviderId(provider);
    if (!targetProvider) return [];

    const registry = await loadModelRegistry();
    const merged = new Map<string, ProviderModelOption>();

    for (const item of registry.models || []) {
      const providerId = normalizeProviderId(
        typeof item?.provider === 'string' ? item.provider : '',
      );
      const modelName = typeof item?.name === 'string' ? item.name.trim() : '';
      if (!providerId || !modelName || providerId !== targetProvider) {
        continue;
      }

      const incoming: ProviderModelOption = {
        name: modelName,
        provider: providerId,
        health: normalizeHealth(item?.health),
        isSelectable: isSelectableFlag(item?.is_selectable),
        healthReason:
          typeof item?.health_reason === 'string' ? item.health_reason : null,
      };

      const existing = merged.get(modelName);
      if (!existing) {
        merged.set(modelName, incoming);
        continue;
      }

      const upgradedSelectable = existing.isSelectable || incoming.isSelectable;
      merged.set(modelName, {
        ...existing,
        isSelectable: upgradedSelectable,
        health: upgradedSelectable ? 'healthy' : incoming.health || existing.health,
        healthReason: upgradedSelectable
          ? null
          : incoming.healthReason || existing.healthReason || null,
      });
    }

    return Array.from(merged.values()).sort((a, b) => a.name.localeCompare(b.name));
  },

  async getProviderModels(provider: string): Promise<string[]> {
    const options = await this.getProviderModelOptions(provider);
    return options.filter(option => option.isSelectable).map(option => option.name);
  },

  async executeTask(): Promise<string> {
    return 'Runtime unavailable in this build.';
  },

  async executeTaskStreaming(
    _goblin: string,
    _task: string,
    onChunk: (chunk: StreamChunk) => void,
    onComplete?: (response: TaskResponse) => void,
  ): Promise<void> {
    onChunk({
      content: 'Runtime streaming unavailable in this build.',
      done: true,
    });
    onComplete?.({ result: { message: 'Runtime streaming unavailable.' } });
  },

  async setProviderApiKey(provider: string, key: string): Promise<void> {
    safeLocalStorage.set(storeKey(provider), key);
  },

  async storeApiKey(provider: string, key: string): Promise<void> {
    safeLocalStorage.set(storeKey(provider), key);
  },

  async getApiKey(provider: string): Promise<string | null> {
    return safeLocalStorage.get(storeKey(provider));
  },

  async clearApiKey(provider: string): Promise<void> {
    safeLocalStorage.remove(storeKey(provider));
  },

  async getHistory(): Promise<MemoryEntry[]> {
    return [];
  },

  async getStats(): Promise<GoblinStats> {
    return {};
  },

  async getCostSummary(): Promise<CostSummary> {
    return emptyCostSummary;
  },

  async parseOrchestration(): Promise<OrchestrationPlan> {
    return emptyOrchestration;
  },

  async onTaskStream(): Promise<void> {
    return;
  },

  async login(email: string, password: string) {
    return apiClient.login(email, password) as Promise<{
      token: string;
      user: any;
    }>;
  },

  async register(email: string, password: string, name?: string) {
    void name;
    return apiClient.register(email, password) as Promise<{
      token: string;
      user: any;
    }>;
  },

  async logout(): Promise<void> {
    return;
  },

  async validateToken(token: string): Promise<{ valid: boolean; user?: any }> {
    return { valid: Boolean(token) };
  },
};

export { apiClient };

export const runtimeClient = runtimeClientImpl;
export const runtimeClientDemo = runtimeClientImpl;
