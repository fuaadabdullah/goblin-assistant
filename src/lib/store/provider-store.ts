import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

// Simplified types for now
interface ProviderConfig {
  model: string;
  maxTokens: number;
  temperature: number;
}

type RoutingStrategy = 'round-robin' | 'performance' | 'latency';

interface Provider {
  id: string;
  name: string;
  type: 'openai' | 'anthropic' | 'google' | 'groq' | 'ollama';
  config: ProviderConfig;
  isEnabled: boolean;
  priority: number;
  lastUsed?: Date;
  usageCount: number;
  averageLatency?: number;
  successRate?: number;
}

interface ProviderStore {
  // State
  providers: Provider[];
  routingStrategy: RoutingStrategy;
  selectedProvider?: string;
  isLoading: boolean;
  error?: string;
  
  // Actions
  actions: {
    addProvider: (provider: Omit<Provider, 'id' | 'usageCount'>) => void;
    updateProvider: (id: string, updates: Partial<Provider>) => void;
    removeProvider: (id: string) => void;
    setSelectedProvider: (id: string) => void;
    setRoutingStrategy: (strategy: RoutingStrategy) => void;
    toggleProvider: (id: string) => void;
    recordUsage: (id: string, latency: number, success: boolean) => void;
    getAvailableProviders: () => Provider[];
    getBestProvider: () => Provider | undefined;
    getHealthyProviders: () => Provider[];
    setProviders: (providers: Provider[]) => void;
    updateHealth: (health: any) => void;
    reset: () => void;
  };
}

const defaultProviders: Provider[] = [
  {
    id: 'openai-default',
    name: 'OpenAI GPT-4',
    type: 'openai',
    isEnabled: true,
    priority: 1,
    usageCount: 0,
    config: {
      model: 'gpt-4',
      maxTokens: 4000,
      temperature: 0.7,
    },
  },
  {
    id: 'anthropic-default',
    name: 'Anthropic Claude',
    type: 'anthropic',
    isEnabled: true,
    priority: 2,
    usageCount: 0,
    config: {
      model: 'claude-3-sonnet-20240229',
      maxTokens: 4000,
      temperature: 0.7,
    },
  },
];

const initialState = {
  providers: defaultProviders,
  routingStrategy: 'round-robin' as RoutingStrategy,
  isLoading: false,
};

export const useProviderStore = create<ProviderStore>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,
        actions: {
          addProvider: (provider) =>
            set((state) => ({
              providers: [
                ...state.providers,
                {
                  ...provider,
                  id: `provider-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                  usageCount: 0,
                },
              ],
            })),

          updateProvider: (id, updates) =>
            set((state) => ({
              providers: state.providers.map((p) =>
                p.id === id ? { ...p, ...updates } : p
              ),
            })),

          removeProvider: (id) =>
            set((state) => ({
              providers: state.providers.filter((p) => p.id !== id),
            })),

          setSelectedProvider: (id) =>
            set({ selectedProvider: id }),

          setRoutingStrategy: (strategy) =>
            set({ routingStrategy: strategy }),

          toggleProvider: (id) =>
            set((state) => ({
              providers: state.providers.map((p) =>
                p.id === id ? { ...p, isEnabled: !p.isEnabled } : p
              ),
            })),

          recordUsage: (id, latency, success) =>
            set((state) => ({
              providers: state.providers.map((p) =>
                p.id === id
                  ? {
                      ...p,
                      usageCount: p.usageCount + 1,
                      lastUsed: new Date(),
                      averageLatency: p.averageLatency
                        ? (p.averageLatency + latency) / 2
                        : latency,
                      successRate: p.successRate
                        ? ((p.successRate * p.usageCount) + (success ? 1 : 0)) / (p.usageCount + 1)
                        : success ? 1 : 0,
                    }
                  : p
              ),
            })),

          getAvailableProviders: () => {
            const { providers } = get();
            return providers.filter((p) => p.isEnabled);
          },

          getBestProvider: () => {
            const { providers, routingStrategy } = get();
            const availableProviders = providers.filter((p) => p.isEnabled);
            
            if (availableProviders.length === 0) return undefined;

            switch (routingStrategy) {
              case 'round-robin':
                return availableProviders.sort((a, b) => a.priority - b.priority)[0];
              
              case 'performance':
                return availableProviders
                  .sort((a, b) => (b.successRate || 0) - (a.successRate || 0))[0];
              
              case 'latency':
                return availableProviders
                  .sort((a, b) => (a.averageLatency || Infinity) - (b.averageLatency || Infinity))[0];
              
              default:
                return availableProviders[0];
            }
          },

          getHealthyProviders: () => {
            const { providers } = get();
            return providers.filter((p) => p.isEnabled);
          },

          setProviders: (providers) =>
            set(() => ({
              providers,
            })),

          updateHealth: (health) =>
            set((state) => ({
              // Update health status based on health data
              providers: state.providers.map((p) => ({
                ...p,
                // Update health status based on health data
                isEnabled: health[p.id]?.status === 'healthy' ? p.isEnabled : p.isEnabled,
              })),
            })),

          reset: () =>
            set(initialState),
        },
      }),
      {
        name: 'provider-store',
        partialize: (state) => ({
          providers: state.providers,
          routingStrategy: state.routingStrategy,
          selectedProvider: state.selectedProvider,
        }),
      }
    ),
    { name: 'provider-store' }
  )
);

// Export hooks for convenience
export const { actions } = useProviderStore.getState();
export const providers = useProviderStore.getState().providers;
export const routingStrategy = useProviderStore.getState().routingStrategy;
