import React, { createContext, useContext, useState, ReactNode } from 'react';
import { useProviderHealth, type ProviderConfig } from '@/hooks/useProviderHealth';
import { useProviderSelection } from '@/hooks/useProviderSelection';

export type { ProviderConfig };

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

export const ProviderProvider: React.FC<ProviderProviderProps> = ({ children }) => {
  // Registry data: providers, models, configs, health
  const health = useProviderHealth();

  // Selection + localStorage persistence
  const selection = useProviderSelection({
    providers: health.providers,
    models: health.models,
  });

  // Retained for backward compatibility — consumers can override lists
  const [loadingModels, setLoadingModels] = useState(false);

  return (
    <ProviderContext.Provider
      value={{
        providers: health.providers,
        models: health.models,
        providerConfigs: health.providerConfigs,
        selectedProvider: selection.selectedProvider,
        selectedModel: selection.selectedModel,
        setSelectedProvider: selection.setSelectedProvider,
        setSelectedModel: selection.setSelectedModel,
        loadingProviders: health.loadingProviders,
        loadingModels,
        setLoadingProviders: () => {},
        setLoadingModels,
        updateProviders: selection.updateProviders,
        updateModels: () => {},
        providerError: health.providerError,
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
