import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface ProviderConfig {
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

interface ProviderContextType {
  // Available providers and models
  providers: string[];
  models: string[];
  providerConfigs: Map<string, ProviderConfig>;

  // Selected values
  selectedProvider: string;
  selectedModel: string;

  // Setters
  setSelectedProvider: (provider: string) => void;
  setSelectedModel: (model: string) => void;

  // Loading states
  loadingProviders: boolean;
  loadingModels: boolean;
  setLoadingProviders: (loading: boolean) => void;
  setLoadingModels: (loading: boolean) => void;

  // Update available options
  updateProviders: (providers: string[]) => void;
  updateModels: (models: string[]) => void;
  
  // Error state
  providerError: string | null;
}

const ProviderContext = createContext<ProviderContextType | undefined>(undefined);

interface ProviderProviderProps {
  children: ReactNode;
}

const normalizeProviderId = (value: string): string => {
  const raw = (value || '').trim().toLowerCase();
  if (!raw) return '';
  const aliases: Record<string, string> = {
    'ollama-gcp': 'ollama_gcp',
    'llamacpp-gcp': 'llamacpp_gcp',
    'azure-openai': 'azure_openai',
    azure: 'azure_openai',
    alibaba: 'aliyun',
    'ali-baba': 'aliyun',
    'aliyun-model-server': 'aliyun',
  };
  return (aliases[raw] || raw).replace(/-/g, '_');
};

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

const normalizeHealth = (value: unknown): string => {
  const normalized = typeof value === 'string' ? value.trim().toLowerCase() : '';
  return normalized || 'unknown';
};

const isSelectable = (value: unknown): boolean => value !== false;

export const ProviderProvider: React.FC<ProviderProviderProps> = ({ children }) => {
  const [providers, setProviders] = useState<string[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [providerConfigs, setProviderConfigs] = useState<Map<string, ProviderConfig>>(new Map());
  const [selectedProvider, setSelectedProviderState] = useState<string>('');
  const [selectedModel, setSelectedModelState] = useState<string>('');
  const [loadingProviders, setLoadingProviders] = useState(false);
  const [loadingModels, setLoadingModels] = useState(false);
  const [providerError, setProviderError] = useState<string | null>(null);

  // Load providers/models from backend registry (single source of truth).
  useEffect(() => {
    const loadProvidersFromBackend = async (): Promise<void> => {
      setLoadingProviders(true);
      setProviderError(null);

      try {
        const response = await fetch('/api/models');
        if (!response.ok) {
          throw new Error(`Failed to fetch model registry (${response.status} ${response.statusText})`);
        }

        const data = (await response.json()) as ModelsRegistryResponse;
        const registryModels = Array.isArray(data?.models) ? data.models : [];
        const registryProviders = Array.isArray(data?.providers) ? data.providers : [];

        const providerSet = new Set<string>();
        const providerNames: string[] = [];
        const providerModelMap = new Map<string, Map<string, RegistryModel>>();
        const modelSet = new Set<string>();
        const configMap = new Map<string, ProviderConfig>();

        for (const providerEntry of registryProviders) {
          const provider = normalizeProviderId(
            typeof providerEntry?.id === 'string' ? providerEntry.id : '',
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

        setProviders(providerNames);
        setModels(Array.from(modelSet));
        setProviderConfigs(configMap);
      } catch (error) {
        console.error('Error loading providers:', error);
        setProviderError(error instanceof Error ? error.message : 'Unknown error loading providers');
        setProviders([]);
        setModels([]);
        setProviderConfigs(new Map());
      } finally {
        setLoadingProviders(false);
      }
    };

    if (typeof window !== 'undefined') {
      loadProvidersFromBackend();
    }
  }, []);

  // Load from localStorage on mount (SSR safe)
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const storedProvider = normalizeProviderId(localStorage.getItem('selectedProvider') || '');
    const storedModel = localStorage.getItem('selectedModel');

    if (providers.length === 0) {
      setSelectedProviderState('');
      setSelectedModelState('');
      return;
    }

    if (storedProvider && providers.includes(storedProvider)) {
      setSelectedProviderState(storedProvider);
    } else {
      setSelectedProviderState(providers[0]);
    }

    if (storedModel && models.includes(storedModel)) {
      setSelectedModelState(storedModel);
    } else {
      setSelectedModelState('');
    }
  }, [providers, models]);

  // Save to localStorage when values change (SSR safe)
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (selectedProvider) {
      localStorage.setItem('selectedProvider', selectedProvider);
    }
  }, [selectedProvider]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (selectedModel) {
      localStorage.setItem('selectedModel', selectedModel);
    }
  }, [selectedModel]);

  const setSelectedProvider = (provider: string) => {
    const canonical = normalizeProviderId(provider);
    setSelectedProviderState(canonical);
    // Clear model when provider changes
    if (canonical !== selectedProvider) {
      setSelectedModelState('');
    }
  };

  const setSelectedModel = (model: string) => {
    setSelectedModelState(model);
  };

  const updateProviders = (newProviders: string[]) => {
    const canonical = Array.from(
      new Set(newProviders.map(p => normalizeProviderId(p)).filter(Boolean))
    );
    setProviders(canonical);
  };

  const updateModels = (newModels: string[]) => {
    setModels(newModels);
  };

  return (
    <ProviderContext.Provider
      value={{
        providers,
        models,
        providerConfigs,
        selectedProvider,
        selectedModel,
        setSelectedProvider,
        setSelectedModel,
        loadingProviders,
        loadingModels,
        setLoadingProviders,
        setLoadingModels,
        updateProviders,
        updateModels,
        providerError,
      }}
    >
      {children}
    </ProviderContext.Provider>
  );
};

export const useProvider = () => {
  const context = useContext(ProviderContext);
  if (!context) {
    throw new Error('useProvider must be used within a ProviderProvider');
  }
  return context;
};
