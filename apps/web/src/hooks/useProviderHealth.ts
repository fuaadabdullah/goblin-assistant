import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api';
import { queryKeys } from '@/lib/query-keys';
import {
  normalizeProviderId,
  PROVIDER_ID_ALIASES,
} from '@/lib/providers/normalizeProvider';

interface RegistryModel {
  name?: string;
  provider?: string;
  health?: string;
  is_selectable?: boolean;
  health_reason?: string | null;
}

interface RegistryProvider {
  id?: string;
  health?: string;
  is_selectable?: boolean;
  health_reason?: string | null;
  configured?: boolean;
}

interface ModelsRegistryResponse {
  models?: RegistryModel[];
  providers?: RegistryProvider[];
  source?: string;
}

export interface ProviderConfig {
  name: string;
  endpoint: string;
  api_key_env?: string;
  models: string[];
  priority_tier: number;
  capabilities: string[];
  is_active: boolean;
  display_name?: string;
  cost_score?: number;
  health?: string;
  is_selectable?: boolean;
  health_reason?: string | null;
  model_metadata?: Record<
    string,
    {
      health: string;
      is_selectable: boolean;
      health_reason?: string | null;
    }
  >;
}

const normalizeHealth = (value: unknown): string => {
  const normalized = typeof value === 'string' ? value.trim().toLowerCase() : '';
  return normalized || 'unknown';
};

const isSelectable = (value: unknown): boolean => value !== false;

export function useProviderHealth() {
  const registryQuery = useQuery<ModelsRegistryResponse>({
    queryKey: queryKeys.models,
    queryFn: async () => (await apiClient.getModelConfigs()) as ModelsRegistryResponse,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const data = registryQuery.data;
  const registryModels = Array.isArray(data?.models) ? data.models : [];
  const registryProviders = Array.isArray(data?.providers) ? data.providers : [];

  const providerSet = new Set<string>();
  const providerNames: string[] = [];
  const providerModelMap = new Map<string, Map<string, RegistryModel>>();
  const modelSet = new Set<string>();
  const configMap = new Map<string, ProviderConfig>();

  if (data) {
    for (const providerEntry of registryProviders) {
      const provider = normalizeProviderId(
        typeof providerEntry?.id === 'string' ? providerEntry.id : '',
        PROVIDER_ID_ALIASES,
      );
      if (!provider) continue;

      if (!providerSet.has(provider)) {
        providerSet.add(provider);
        providerNames.push(provider);
      }

      configMap.set(provider, {
        name: provider,
        endpoint: '',
        models: [],
        priority_tier: 0,
        capabilities: ['chat'],
        is_active: true,
        display_name: provider.replace(/_/g, ' '),
        health: normalizeHealth(providerEntry?.health),
        is_selectable: isSelectable(providerEntry?.is_selectable),
        health_reason:
          typeof providerEntry?.health_reason === 'string'
            ? providerEntry.health_reason
            : null,
        model_metadata: {},
      });
    }

    for (const item of registryModels) {
      const provider = normalizeProviderId(
        typeof item?.provider === 'string' ? item.provider : '',
        PROVIDER_ID_ALIASES,
      );
      const model = typeof item?.name === 'string' ? item.name.trim() : '';
      if (!provider || !model) continue;

      if (!providerSet.has(provider)) {
        providerSet.add(provider);
        providerNames.push(provider);
      }
      modelSet.add(model);

      if (!providerModelMap.has(provider)) {
        providerModelMap.set(provider, new Map<string, RegistryModel>());
      }
      const modelMap = providerModelMap.get(provider);
      if (!modelMap) continue;
      const existing = modelMap.get(model);
      const incomingSelectable = isSelectable(item?.is_selectable);
      if (!existing || (!isSelectable(existing?.is_selectable) && incomingSelectable)) {
        modelMap.set(model, item);
      }
    }

    for (const [provider, providerModels] of providerModelMap.entries()) {
      const existing = configMap.get(provider);
      const metadata: Record<
        string,
        {
          health: string;
          is_selectable: boolean;
          health_reason?: string | null;
        }
      > = {};
      for (const [modelName, meta] of providerModels.entries()) {
        metadata[modelName] = {
          health: normalizeHealth(meta?.health),
          is_selectable: isSelectable(meta?.is_selectable),
          health_reason:
            typeof meta?.health_reason === 'string' ? meta.health_reason : null,
        };
      }

      configMap.set(provider, {
        name: existing?.name || provider,
        endpoint: existing?.endpoint || '',
        models: Array.from(providerModels.keys()).sort(),
        priority_tier: existing?.priority_tier ?? 0,
        capabilities: existing?.capabilities || ['chat'],
        is_active: existing?.is_active ?? true,
        display_name: existing?.display_name || provider.replace(/_/g, ' '),
        health: existing?.health || 'unknown',
        is_selectable: existing?.is_selectable ?? true,
        health_reason: existing?.health_reason || null,
        model_metadata: metadata,
      });
    }
  }

  const error = registryQuery.error
    ? registryQuery.error instanceof Error
      ? registryQuery.error.message
      : 'Unknown error loading providers'
    : null;

  return {
    providers: providerNames,
    models: Array.from(modelSet),
    providerConfigs: configMap,
    loadingProviders: registryQuery.isLoading || registryQuery.isFetching,
    providerError: data ? null : error,
  };
}
