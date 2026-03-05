// lib/store/analytics-store.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UsageMetrics {
  totalRequests: number;
  totalTokens: number;
  totalCost: number;
  averageLatency: number;
  requestsByProvider: Record<string, number>;
  tokensByProvider: Record<string, number>;
  costByProvider: Record<string, number>;
  requestsByDay: Record<string, number>;
}

interface AnalyticsStore {
  metrics: UsageMetrics;
  isLoading: boolean;

  actions: {
    updateMetrics: (metrics: Partial<UsageMetrics>) => void;
    incrementRequest: (provider: string, tokens: number, cost: number, latency: number) => void;
    resetMetrics: () => void;
    setLoading: (loading: boolean) => void;
  };
}

const defaultMetrics: UsageMetrics = {
  totalRequests: 0,
  totalTokens: 0,
  totalCost: 0,
  averageLatency: 0,
  requestsByProvider: {},
  tokensByProvider: {},
  costByProvider: {},
  requestsByDay: {},
};

export const useAnalyticsStore = create<AnalyticsStore>()(
  persist(
    (set, _get) => ({
      metrics: defaultMetrics,
      isLoading: false,

      actions: {
        updateMetrics: (newMetrics) => {
          set(state => ({
            metrics: { ...state.metrics, ...newMetrics },
          }));
        },

        incrementRequest: (_provider, _tokens, _cost, _latency) => {
          const today = new Date().toISOString().split('T')[0];

          set(state => {
            const currentMetrics = state.metrics;
            const requestCount = currentMetrics.requestsByProvider[_provider] || 0;
            const tokenCount = currentMetrics.tokensByProvider[_provider] || 0;
            const costAmount = currentMetrics.costByProvider[_provider] || 0;
            const dayCount = currentMetrics.requestsByDay[today] || 0;

            const newRequestsByProvider = {
              ...currentMetrics.requestsByProvider,
              [_provider]: requestCount + 1,
            };

            const newTokensByProvider = {
              ...currentMetrics.tokensByProvider,
              [_provider]: tokenCount + _tokens,
            };

            const newCostByProvider = {
              ...currentMetrics.costByProvider,
              [_provider]: costAmount + _cost,
            };

            const newRequestsByDay = {
              ...currentMetrics.requestsByDay,
              [today]: dayCount + 1,
            };

            // Calculate new average latency
            const totalRequests = currentMetrics.totalRequests + 1;
            const newAverageLatency =
              (currentMetrics.averageLatency * currentMetrics.totalRequests + _latency) / totalRequests;

            return {
              metrics: {
                ...currentMetrics,
                totalRequests,
                totalTokens: currentMetrics.totalTokens + _tokens,
                totalCost: currentMetrics.totalCost + _cost,
                averageLatency: newAverageLatency,
                requestsByProvider: newRequestsByProvider,
                tokensByProvider: newTokensByProvider,
                costByProvider: newCostByProvider,
                requestsByDay: newRequestsByDay,
              },
            };
          });
        },

        resetMetrics: () => {
          set({ metrics: defaultMetrics });
        },

        setLoading: (loading) => {
          set({ isLoading: loading });
        },
      },
    }),
    {
      name: 'analytics-storage',
    }
  )
);
