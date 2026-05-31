import {
  ProviderUpdatePayload,
  getBackend,
  getFrontend,
  patchBackend,
  postBackend,
} from './shared';
import { normalizeProviderId } from '../providers/normalizeProvider';
import type { CostSummary, ProviderModelOption } from '../../types/api';

type ModelRegistryItem = {
  name?: string;
  provider?: string;
  health?: string;
  is_selectable?: boolean;
  health_reason?: string | null;
};

type ProviderRegistryItem = {
  id?: string;
};

type ModelRegistryResponse = {
  models?: ModelRegistryItem[];
  providers?: ProviderRegistryItem[];
};

const normalizeHealth = (value: unknown): string => {
  const s = typeof value === 'string' ? value.trim().toLowerCase() : '';
  return s || 'unknown';
};

const isSelectableFlag = (value: unknown): boolean => value !== false;

async function loadModelRegistry(): Promise<ModelRegistryResponse> {
  try {
    const data = await getFrontend<ModelRegistryResponse>('/api/models');
    return {
      models: Array.isArray(data?.models) ? data.models : [],
      providers: Array.isArray(data?.providers) ? data.providers : [],
    };
  } catch {
    return { models: [], providers: [] };
  }
}

const emptyCostSummary: CostSummary = {
  total_cost: 0,
  cost_by_provider: {},
  cost_by_model: {},
  requests_by_provider: {},
};

export const providersMethods = {
  async getProviderSettings() {
    return getBackend('/providers');
  },

  async getModelConfigs() {
    return getFrontend('/api/models');
  },

  async getGlobalSettings() {
    return getBackend('/settings');
  },

  async updateProvider(providerId: string | number, provider: ProviderUpdatePayload) {
    return patchBackend(`/providers/${providerId}`, provider);
  },

  async updateGlobalSetting(key: string, value: unknown) {
    return patchBackend(`/settings/${encodeURIComponent(key)}`, { value });
  },

  async setProviderPriority(providerId: number, priority: number, role?: string) {
    return postBackend(`/providers/${providerId}/priority`, { priority, role });
  },

  async reorderProviders(providerIds: number[]) {
    return postBackend('/providers/reorder', { providerIds });
  },

  async testProviderConnection(providerId: number | string) {
    return postBackend(`/providers/${providerId}/test`);
  },

  async testProviderWithPrompt(providerId: number | string, prompt: string) {
    return postBackend(`/providers/${providerId}/test-prompt`, { prompt });
  },

  async getProviders(): Promise<string[]> {
    const registry = await loadModelRegistry();
    const seen = new Set<string>();
    const providers: string[] = [];

    for (const entry of registry.providers ?? []) {
      const id = normalizeProviderId(typeof entry?.id === 'string' ? entry.id : '');
      if (!id || seen.has(id)) continue;
      seen.add(id);
      providers.push(id);
    }

    if (providers.length > 0) return providers;

    for (const item of registry.models ?? []) {
      const id = normalizeProviderId(typeof item?.provider === 'string' ? item.provider : '');
      if (!id || seen.has(id)) continue;
      seen.add(id);
      providers.push(id);
    }

    return providers;
  },

  async getProviderModelOptions(provider: string): Promise<ProviderModelOption[]> {
    const target = normalizeProviderId(provider);
    if (!target) return [];

    const registry = await loadModelRegistry();
    const merged = new Map<string, ProviderModelOption>();

    for (const item of registry.models ?? []) {
      const pid = normalizeProviderId(typeof item?.provider === 'string' ? item.provider : '');
      const name = typeof item?.name === 'string' ? item.name.trim() : '';
      if (!pid || !name || pid !== target) continue;

      const incoming: ProviderModelOption = {
        name,
        provider: pid,
        health: normalizeHealth(item?.health),
        isSelectable: isSelectableFlag(item?.is_selectable),
        healthReason: typeof item?.health_reason === 'string' ? item.health_reason : null,
      };

      const existing = merged.get(name);
      if (!existing) {
        merged.set(name, incoming);
        continue;
      }

      const selectable = existing.isSelectable || incoming.isSelectable;
      merged.set(name, {
        ...existing,
        isSelectable: selectable,
        health: selectable ? 'healthy' : incoming.health || existing.health,
        healthReason: selectable ? null : incoming.healthReason ?? existing.healthReason ?? null,
      });
    }

    return Array.from(merged.values()).sort((a, b) => a.name.localeCompare(b.name));
  },

  async getProviderModels(provider: string): Promise<string[]> {
    const options = await providersMethods.getProviderModelOptions(provider);
    return options.filter((o) => o.isSelectable).map((o) => o.name);
  },

  async getCostSummary(): Promise<CostSummary> {
    try {
      return await getBackend<CostSummary>('/costs/summary');
    } catch {
      return emptyCostSummary;
    }
  },
};
