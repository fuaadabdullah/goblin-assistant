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
} from "../types/api";
import { apiClient } from "../api/apiClient";

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

const keyPrefix = "goblin_provider_key:";

const storeKey = (provider: string) => `${keyPrefix}${provider}`;

const normalizeProviderId = (value: string): string => {
  const raw = (value || "").trim().toLowerCase();
  if (!raw) return "";
  return raw.replace(/-/g, "_");
};

async function loadModelRegistry(): Promise<ModelRegistryResponse> {
  try {
    const response = await fetch("/api/models", { method: "GET" });
    if (!response.ok) {
      return { models: [], providers: [] };
    }

    const payload = (await response.json()) as ModelRegistryResponse;
    return {
      models: Array.isArray(payload?.models) ? payload.models : [],
      providers: Array.isArray(payload?.providers) ? payload.providers : [],
    };
  } catch {
    return { models: [], providers: [] };
  }
}

const normalizeHealth = (value: unknown): string => {
  const normalized = typeof value === "string" ? value.trim().toLowerCase() : "";
  return normalized || "unknown";
};

const isSelectableFlag = (value: unknown): boolean => value !== false;

const safeLocalStorage = {
  get(key: string): string | null {
    if (typeof window === "undefined") return null;
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key: string, value: string): void {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(key, value);
    } catch {
      return;
    }
  },
  remove(key: string): void {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.removeItem(key);
    } catch {
      return;
    }
  },
};

const emptyCostSummary: CostSummary = {
  total_cost: 0,
  cost_by_provider: {},
  cost_by_model: {},
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
        typeof providerEntry?.id === "string" ? providerEntry.id : "",
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
        typeof item?.provider === "string" ? item.provider : "",
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
        typeof item?.provider === "string" ? item.provider : "",
      );
      const modelName = typeof item?.name === "string" ? item.name.trim() : "";
      if (!providerId || !modelName || providerId !== targetProvider) {
        continue;
      }

      const incoming: ProviderModelOption = {
        name: modelName,
        provider: providerId,
        health: normalizeHealth(item?.health),
        isSelectable: isSelectableFlag(item?.is_selectable),
        healthReason:
          typeof item?.health_reason === "string" ? item.health_reason : null,
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
        health: upgradedSelectable ? "healthy" : incoming.health || existing.health,
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
    return "Runtime unavailable in this build.";
  },

  async executeTaskStreaming(
    _goblin: string,
    _task: string,
    onChunk: (chunk: StreamChunk) => void,
    onComplete?: (response: TaskResponse) => void,
  ): Promise<void> {
    onChunk({
      content: "Runtime streaming unavailable in this build.",
      done: true,
    });
    onComplete?.({ result: { message: "Runtime streaming unavailable." } });
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

export const runtimeClient = runtimeClientImpl;
export const runtimeClientDemo = runtimeClientImpl;
