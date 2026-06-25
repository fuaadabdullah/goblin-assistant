import {
  ProviderUpdatePayload,
  V1_API_PREFIX,
  getBackend,
  getFrontend,
  patchBackend,
  postBackend,
  putBackend,
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
    const registryResponse = await getFrontend<ModelRegistryResponse>('/api/models');
    return {
      models: Array.isArray(registryResponse?.models) ? registryResponse.models : [],
      providers: Array.isArray(registryResponse?.providers) ? registryResponse.providers : [],
    };
  } catch {
    return { models: [], providers: [] };
  }
}

const collectRegistryProviderIds = (items: ProviderRegistryItem[]) => {
  const seen = new Set<string>();
  const ids: string[] = [];

  for (const item of items) {
    const id = normalizeProviderId(typeof item?.id === 'string' ? item.id : '');
    if (!id || seen.has(id)) continue;
    seen.add(id);
    ids.push(id);
  }

  return ids;
};

const collectModelProviderIds = (items: ModelRegistryItem[]) => {
  const seen = new Set<string>();
  const ids: string[] = [];

  for (const item of items) {
    const id = normalizeProviderId(typeof item?.provider === 'string' ? item.provider : '');
    if (!id || seen.has(id)) continue;
    seen.add(id);
    ids.push(id);
  }

  return ids;
};

const toProviderModelOption = (item: ModelRegistryItem): ProviderModelOption => ({
  name: typeof item?.name === 'string' ? item.name.trim() : '',
  provider: normalizeProviderId(typeof item?.provider === 'string' ? item.provider : ''),
  health: normalizeHealth(item?.health),
  isSelectable: isSelectableFlag(item?.is_selectable),
  healthReason: typeof item?.health_reason === 'string' ? item.health_reason : null,
});

const mergeProviderModelOption = (
  merged: Map<string, ProviderModelOption>,
  incoming: ProviderModelOption
) => {
  const existing = merged.get(incoming.name);
  if (!existing) {
    merged.set(incoming.name, incoming);
    return;
  }

  const selectable = existing.isSelectable || incoming.isSelectable;
  merged.set(incoming.name, {
    ...existing,
    isSelectable: selectable,
    health: selectable ? 'healthy' : incoming.health || existing.health,
    healthReason: selectable ? null : (incoming.healthReason ?? existing.healthReason ?? null),
  });
};

const mergeSelectableModelOptions = (items: ModelRegistryItem[], target: string) => {
  const merged = new Map<string, ProviderModelOption>();

  for (const item of items) {
    const incoming = toProviderModelOption(item);
    const { provider: pid, name } = incoming;
    if (!pid || !name || pid !== target) continue;

    mergeProviderModelOption(merged, incoming);
  }

  return Array.from(merged.values()).sort((a, b) => a.name.localeCompare(b.name));
};

const emptyCostSummary: CostSummary = {
  total_cost: 0,
  cost_by_provider: {},
  cost_by_model: {},
  requests_by_provider: {},
};

export const providersMethods = {
  async getProviderSettings() {
    return getBackend(`${V1_API_PREFIX}/settings/`);
  },

  async getModelConfigs() {
    return getFrontend('/api/models');
  },

  async getGlobalSettings() {
    return getBackend(`${V1_API_PREFIX}/settings/`);
  },

  async updateProvider(providerId: string | number, provider: ProviderUpdatePayload) {
    return putBackend(`${V1_API_PREFIX}/settings/providers/${providerId}`, provider);
  },

  async updateGlobalSetting(key: string, value: unknown) {
    return patchBackend(`${V1_API_PREFIX}/settings/${encodeURIComponent(key)}`, { value });
  },

  async setProviderPriority(providerId: number, priority: number, role?: string) {
    return postBackend(`${V1_API_PREFIX}/providers/${providerId}/priority`, { priority, role });
  },

  async reorderProviders(providerIds: number[]) {
    return postBackend(`${V1_API_PREFIX}/providers/reorder`, { providerIds });
  },

  async testProviderConnection(providerId: number | string) {
    return postBackend(`${V1_API_PREFIX}/providers/${providerId}/test`);
  },

  async testProviderWithPrompt(providerId: number | string, prompt: string) {
    return postBackend(`${V1_API_PREFIX}/providers/${providerId}/test-prompt`, { prompt });
  },

  async getProviders(): Promise<string[]> {
    const registry = await loadModelRegistry();
    const providers = collectRegistryProviderIds(registry.providers ?? []);
    if (providers.length > 0) return providers;

    return collectModelProviderIds(registry.models ?? []);
  },

  async getProviderModelOptions(provider: string): Promise<ProviderModelOption[]> {
    const target = normalizeProviderId(provider);
    if (!target) return [];

    const registry = await loadModelRegistry();
    return mergeSelectableModelOptions(registry.models ?? [], target);
  },

  async getProviderModels(provider: string): Promise<string[]> {
    const options = await providersMethods.getProviderModelOptions(provider);
    return options.filter((o) => o.isSelectable).map((o) => o.name);
  },

  async getCostSummary(): Promise<CostSummary> {
    try {
      return await getBackend<CostSummary>(`${V1_API_PREFIX}/costs/summary`);
    } catch {
      return emptyCostSummary;
    }
  },
};
