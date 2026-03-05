// providers/ModelProvider.tsx
'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useProviderStore } from '../lib/store';
import { providerService } from '../../lib/services';
// Define types locally since they're not exported from lib/types
interface ProviderConfig {
  id: string;
  name: string;
  type: 'openai' | 'anthropic' | 'google' | 'groq' | 'ollama';
  description: string;
  isAvailable: boolean;
  models: ModelConfig[];
  costConfig?: {
    inputCostPerToken: number;
    outputCostPerToken: number;
  };
}

interface ModelConfig {
  id: string;
  name: string;
  maxTokens: number;
  temperature: number;
  supportsStreaming: boolean;
}

type RoutingStrategy = 'round-robin' | 'performance' | 'latency';

interface ModelContextType {
  providers: ProviderConfig[];
  selectedProvider: ProviderConfig | null;
  selectedModel: ModelConfig | null;
  routingStrategy: RoutingStrategy;
  isLoading: boolean;
  error: string | null;
  selectProvider: (provider: ProviderConfig) => void;
  selectModel: (model: ModelConfig) => void;
  setRoutingStrategy: (strategy: RoutingStrategy) => void;
  refreshProviders: () => Promise<void>;
  getAvailableModels: (providerId: string) => ModelConfig[];
  getRecommendedProvider: (complexity: 'simple' | 'medium' | 'complex') => ProviderConfig | null;
}

const ModelContext = createContext<ModelContextType | undefined>(undefined);

interface ModelProviderProps {
  children: ReactNode;
}

export function ModelProvider({ children }: ModelProviderProps) {
  const providerStore = useProviderStore();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<ProviderConfig | null>(null);
  const [selectedModel, setSelectedModel] = useState<ModelConfig | null>(null);

  // Load providers and selections on mount
  useEffect(() => {
    refreshProviders();
    loadSelections();
  }, []);

  const loadSelections = () => {
    const savedProviderId = localStorage.getItem('selected-provider');
    const savedModelId = localStorage.getItem('selected-model');

    if (savedProviderId) {
      const provider = providerStore.providers.find(p => p.id === savedProviderId);
      if (provider) {
        // Convert Provider to ProviderConfig
        const providerConfig: ProviderConfig = {
          id: provider.id,
          name: provider.name,
          type: provider.type,
          description: '',
          isAvailable: true,
          models: [],
          costConfig: undefined
        };
        setSelectedProvider(providerConfig);
        if (savedModelId) {
          const model = providerConfig.models.find(m => m.id === savedModelId);
          if (model) {
            setSelectedModel(model);
          }
        }
      }
    }
  };

  const refreshProviders = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [providers, health] = await Promise.all([
        providerService.getProviders(),
        providerService.getProviderHealth(),
      ]);

      // Convert ProviderConfig[] to Provider[] for store
      const convertedProviders = providers.map(p => ({
        id: p.id,
        name: p.name,
        type: p.type as 'openai' | 'anthropic' | 'google' | 'groq' | 'ollama',
        config: {
          model: p.models[0]?.id || 'default',
          maxTokens: p.models[0]?.maxTokens || 4000,
          temperature: 0.7, // Default temperature
        },
        isEnabled: p.isAvailable,
        priority: 1,
        usageCount: 0,
        averageLatency: undefined,
        successRate: undefined,
      }));

      providerStore.actions.setProviders(convertedProviders);
      providerStore.actions.updateHealth(health);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load providers');
    } finally {
      setIsLoading(false);
    }
  };

  const selectProvider = (provider: ProviderConfig) => {
    setSelectedProvider(provider);
    localStorage.setItem('selected-provider', provider.id);
    // Clear selected model if it's not available in the new provider
    if (selectedModel && !provider.models.find(m => m.id === selectedModel.id)) {
      setSelectedModel(null);
      localStorage.removeItem('selected-model');
    }
  };

  const selectModel = (model: ModelConfig) => {
    setSelectedModel(model);
    localStorage.setItem('selected-model', model.id);
  };

  const setRoutingStrategy = (strategy: RoutingStrategy) => {
    providerStore.actions.setRoutingStrategy(strategy);
  };

  const getAvailableModels = (providerId: string): ModelConfig[] => {
    const provider = providerStore.providers.find(p => p.id === providerId);
    // Convert Provider to ProviderConfig and return models
    if (provider) {
      return [{
        id: provider.config.model,
        name: provider.config.model,
        maxTokens: provider.config.maxTokens,
        temperature: provider.config.temperature,
        supportsStreaming: true,
      }];
    }
    return [];
  };

  const getRecommendedProvider = (complexity: 'simple' | 'medium' | 'complex'): ProviderConfig | null => {
    const availableProviders = providerStore.actions.getHealthyProviders();

    if (availableProviders.length === 0) return null;

    // Convert Provider[] to ProviderConfig[] for recommendation logic
    const providerConfigs: ProviderConfig[] = availableProviders.map(p => ({
      id: p.id,
      name: p.name,
      type: p.type,
      description: '',
      isAvailable: p.isEnabled,
      models: [{
        id: p.config.model,
        name: p.config.model,
        maxTokens: p.config.maxTokens,
        temperature: p.config.temperature,
        supportsStreaming: true,
      }],
      costConfig: {
        inputCostPerToken: 0.0001, // Default cost
        outputCostPerToken: 0.0002,
      },
    }));

    switch (complexity) {
      case 'simple':
        // Prefer cheapest provider for simple tasks
        return providerConfigs.reduce((cheapest, current) => {
          const currentCost = current.costConfig?.inputCostPerToken || 0;
          const cheapestCost = cheapest.costConfig?.inputCostPerToken || 0;
          return currentCost < cheapestCost ? current : cheapest;
        });

      case 'medium':
        // Balance cost and performance
        return providerConfigs.find(p => p.type === 'openai') ||
               providerConfigs.find(p => p.type === 'anthropic') ||
               providerConfigs[0];

      case 'complex':
        // Prefer highest performance for complex tasks
        return providerConfigs.find(p => p.type === 'anthropic') ||
               providerConfigs.find(p => p.type === 'openai') ||
               providerConfigs[0];

      default:
        return providerConfigs[0];
    }
  };

  // Convert Provider[] to ProviderConfig[] for context
  const providerConfigs: ProviderConfig[] = providerStore.providers.map(p => ({
    id: p.id,
    name: p.name,
    type: p.type,
    description: '',
    isAvailable: p.isEnabled,
    models: [{
      id: p.config.model,
      name: p.config.model,
      maxTokens: p.config.maxTokens,
      temperature: p.config.temperature,
      supportsStreaming: true,
    }],
    costConfig: {
      inputCostPerToken: 0.0001,
      outputCostPerToken: 0.0002,
    },
  }));

  return (
    <ModelContext.Provider value={{
      providers: providerConfigs,
      selectedProvider,
      selectedModel,
      routingStrategy: providerStore.routingStrategy,
      isLoading,
      error,
      selectProvider,
      selectModel,
      setRoutingStrategy,
      refreshProviders,
      getAvailableModels,
      getRecommendedProvider,
    }}>
      {children}
    </ModelContext.Provider>
  );
}

export function useModel() {
  const context = useContext(ModelContext);
  if (!context) {
    throw new Error('useModel must be used within ModelProvider');
  }
  return context;
}
