/**
 * Thin adapter over the canonical apiClient.
 *
 * All HTTP, retry, auth, and error logic lives in src/lib/api/.
 * This file exists only to preserve the public exports that callers
 * already import from '@/api'. New code should import from '@/lib/api'
 * or '@/lib/provider-keys' directly.
 */

import { apiClient, getBackend, postBackend, putBackend, patchBackend } from '@/lib/api';
import { providerKeys } from '@/lib/provider-keys';
import type {
  CostSummary,
  GoblinStats,
  GoblinStatus,
  LoginResponse,
  MemoryEntry,
  OrchestrationPlan,
  ProviderModelOption,
  RuntimeClient,
  StreamChunk,
  TaskResponse,
  User,
} from '@/types/api';

// Re-export shared types consumed from '@/api'
export type {
  ProviderUpdatePayload,
  PasskeyCredential,
  SandboxRunPayload,
  AccountProfile,
  AccountPreferences,
} from '@/lib/api';

// Re-export apiClient for callers that import it from '@/api'
export { apiClient };

// ---------------------------------------------------------------------------
// RuntimeClient adapter
// Orchestration methods (executeTask, executeTaskStreaming, parseOrchestration,
// getGoblins) are stubs pending backend implementation.
// ---------------------------------------------------------------------------

const runtimeClientImpl: RuntimeClient = {
  async getGoblins(): Promise<GoblinStatus[]> {
    return [];
  },

  async getProviders(): Promise<string[]> {
    return apiClient.getProviders();
  },

  async getProviderModelOptions(provider: string): Promise<ProviderModelOption[]> {
    return apiClient.getProviderModelOptions(provider);
  },

  async getProviderModels(provider: string): Promise<string[]> {
    return apiClient.getProviderModels(provider);
  },

  async executeTask(): Promise<string> {
    return 'Runtime unavailable in this build.';
  },

  async executeTaskStreaming(
    _goblin: string,
    _task: string,
    onChunk: (chunk: StreamChunk) => void,
    onComplete?: (response: TaskResponse) => void
  ): Promise<void> {
    onChunk({ content: 'Runtime streaming unavailable in this build.', done: true });
    onComplete?.({ result: { message: 'Runtime streaming unavailable.' } });
  },

  async setProviderApiKey(provider: string, key: string): Promise<void> {
    providerKeys.set(provider, key);
  },

  async storeApiKey(provider: string, key: string): Promise<void> {
    providerKeys.set(provider, key);
  },

  async getApiKey(provider: string): Promise<string | null> {
    return providerKeys.get(provider);
  },

  async clearApiKey(provider: string): Promise<void> {
    providerKeys.remove(provider);
  },

  async getHistory(): Promise<MemoryEntry[]> {
    return [];
  },

  async getStats(): Promise<GoblinStats> {
    return {};
  },

  async getCostSummary(): Promise<CostSummary> {
    return apiClient.getCostSummary();
  },

  async parseOrchestration(): Promise<OrchestrationPlan> {
    return { steps: [], total_batches: 0, max_parallel: 0 };
  },

  async onTaskStream(): Promise<void> {},

  async login(email: string, password: string): Promise<LoginResponse> {
    return apiClient.login(email, password) as Promise<LoginResponse>;
  },

  async register(email: string, password: string): Promise<LoginResponse> {
    return apiClient.register(email, password) as Promise<LoginResponse>;
  },

  async logout(): Promise<void> {
    await apiClient.logout().catch(() => {});
  },

  async validateToken(token: string): Promise<{ valid: boolean; user?: User }> {
    const result = await apiClient.validateToken(token);
    return { valid: result?.valid ?? false, user: result?.user };
  },
};

export const runtimeClient = runtimeClientImpl;
export const runtimeClientDemo = runtimeClientImpl;

// ---------------------------------------------------------------------------
// api: minimal HTTP shim backed by the canonical axios helpers.
// Used only by raptor.ts — new code should call getBackend/postBackend directly.
// ---------------------------------------------------------------------------

export const api = {
  get: async <T>(path: string) => ({ data: await getBackend<T>(path) }),
  post: async <T = unknown>(path: string, body?: unknown) => ({
    data: await postBackend<T>(path, body),
  }),
  put: async <T = unknown>(path: string, body?: unknown) => ({
    data: await putBackend<T>(path, body),
  }),
  patch: async <T = unknown>(path: string, body?: unknown) => ({
    data: await patchBackend<T>(path, body),
  }),
  delete: async <T = unknown>(path: string) => ({
    data: await getBackend<T>(path),
  }),
};
