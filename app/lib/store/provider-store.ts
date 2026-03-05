// lib/store/provider-store.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ProviderConfig, ProviderHealth, RoutingStrategy } from '../types';

interface ProviderStore {
  providers: ProviderConfig[];
  health: Record<string, ProviderHealth>;
  routingStrategy: RoutingStrategy;

  actions: {
    setProviders: (providers: ProviderConfig[]) => void;
    updateProvider: (providerId: string, updates: Partial<ProviderConfig>) => void;
    updateHealth: (health: ProviderHealth[]) => void;
    setRoutingStrategy: (strategy: RoutingStrategy) => void;
    getHealthyProviders: () => ProviderConfig[];
    getProviderById: (id: string) => ProviderConfig | undefined;
  };
}

export const useProviderStore = create<ProviderStore>()(
  persist(
    (set, get) => ({
      providers: [],
      health: {},
      routingStrategy: { type: 'balanced' },

      actions: {
        setProviders: (providers) => {
          set({ providers });
        },

        updateProvider: (providerId, updates) => {
          set(state => ({
            providers: state.providers.map(provider =>
              provider.id === providerId
                ? { ...provider, ...updates }
                : provider
            ),
          }));
        },

        updateHealth: (healthUpdates) => {
          const healthMap = healthUpdates.reduce((acc, health) => {
            acc[health.providerId] = health;
            return acc;
          }, {} as Record<string, ProviderHealth>);

          set({ health: { ...get().health, ...healthMap } });
        },

        setRoutingStrategy: (strategy) => {
          set({ routingStrategy: strategy });
        },

        getHealthyProviders: () => {
          const { providers, health } = get();
          return providers.filter(provider => {
            const providerHealth = health[provider.id];
            return provider.isEnabled &&
                   (!providerHealth || providerHealth.status === 'healthy');
          });
        },

        getProviderById: (id) => {
          return get().providers.find(provider => provider.id === id);
        },
      },
    }),
    {
      name: 'provider-storage',
      partialize: (state) => ({
        routingStrategy: state.routingStrategy,
      }),
    }
  )
);
