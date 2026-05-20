import { useState, useEffect } from 'react';
import {
  normalizeProviderId,
  PROVIDER_ID_ALIASES,
} from '@/lib/providers/normalizeProvider';

interface UseProviderSelectionOptions {
  providers: string[];
  models: string[];
}

export function useProviderSelection({ providers, models }: UseProviderSelectionOptions) {
  const [selectedProvider, setSelectedProviderState] = useState<string>('');
  const [selectedModel, setSelectedModelState] = useState<string>('');

  // Load from localStorage on mount (SSR safe)
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const storedProvider = normalizeProviderId(
      localStorage.getItem('selectedProvider') || '',
      PROVIDER_ID_ALIASES,
    );
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
    const canonical = normalizeProviderId(provider, PROVIDER_ID_ALIASES);
    if (canonical !== selectedProvider) {
      setSelectedModelState('');
    }
    setSelectedProviderState(canonical);
  };

  const setSelectedModel = (model: string) => {
    setSelectedModelState(model);
  };

  const updateProviders = (newProviders: string[]) => {
    return Array.from(
      new Set(newProviders.map(p => normalizeProviderId(p, PROVIDER_ID_ALIASES)).filter(Boolean)),
    );
  };

  return {
    selectedProvider,
    selectedModel,
    setSelectedProvider,
    setSelectedModel,
    updateProviders,
  };
}
