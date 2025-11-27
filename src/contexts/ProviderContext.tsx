import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface ProviderContextType {
  // Available providers and models
  providers: string[];
  models: string[];

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
}

const ProviderContext = createContext<ProviderContextType | undefined>(undefined);

interface ProviderProviderProps {
  children: ReactNode;
}

export const ProviderProvider: React.FC<ProviderProviderProps> = ({ children }) => {
  const [providers, setProviders] = useState<string[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [selectedProvider, setSelectedProviderState] = useState<string>('');
  const [selectedModel, setSelectedModelState] = useState<string>('');
  const [loadingProviders, setLoadingProviders] = useState(false);
  const [loadingModels, setLoadingModels] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    const storedProvider = localStorage.getItem('selectedProvider');
    const storedModel = localStorage.getItem('selectedModel');

    if (storedProvider) {
      setSelectedProviderState(storedProvider);
    }
    if (storedModel) {
      setSelectedModelState(storedModel);
    }
  }, []);

  // Save to localStorage when values change
  useEffect(() => {
    if (selectedProvider) {
      localStorage.setItem('selectedProvider', selectedProvider);
    }
  }, [selectedProvider]);

  useEffect(() => {
    if (selectedModel) {
      localStorage.setItem('selectedModel', selectedModel);
    }
  }, [selectedModel]);

  const setSelectedProvider = (provider: string) => {
    setSelectedProviderState(provider);
    // Clear model when provider changes
    if (provider !== selectedProvider) {
      setSelectedModelState('');
    }
  };

  const setSelectedModel = (model: string) => {
    setSelectedModelState(model);
  };

  const updateProviders = (newProviders: string[]) => {
    setProviders(newProviders);
  };

  const updateModels = (newModels: string[]) => {
    setModels(newModels);
  };

  return (
    <ProviderContext.Provider
      value={{
        providers,
        models,
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
