import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { runtimeClient } from '@/lib/api/runtimeClient';
import { getUserMessage } from '@/lib/error/toast';
import { queryKeys } from '../lib/query-keys';
import type { ModelUsageRollupResponse } from '@/types/api';
import type { CostSummary } from '@/types/api';

export interface ServiceStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  latency?: number;
  message?: string;
}

export interface DashboardData {
  cost: {
    total: number;
    today: number;
    thisMonth: number;
    byProvider: Record<string, number>;
  };
  backend: ServiceStatus;
  vectorStore: ServiceStatus;
  mcp: ServiceStatus;
  rag: ServiceStatus;
  sandbox: ServiceStatus;
  observability: {
    modelUsage: ModelUsageRollupResponse | null;
    metricsPreview: string;
  };
}

const defaultService: ServiceStatus = { status: 'healthy', latency: 120 };

const toServiceStatus = (
  service:
    | {
        status?: string;
        latency?: number;
        message?: string;
      }
    | undefined
): ServiceStatus => {
  if (!service) return defaultService;
  if (service.status === 'healthy' || service.status === 'unhealthy') {
    return service as ServiceStatus;
  }
  if (service.status === 'degraded' || service.status === 'warnings') {
    return { ...service, status: 'degraded' };
  }
  return { ...service, status: 'degraded', message: service.message ?? 'Status unknown' };
};

const defaultObservability = {
  modelUsage: null as ModelUsageRollupResponse | null,
  metricsPreview: '',
};

const zeroCost: DashboardData['cost'] = {
  total: 0,
  today: 0,
  thisMonth: 0,
  byProvider: {},
};

function toDashboardCost(
  costSummary: CostSummary | null | undefined,
  modelUsage: ModelUsageRollupResponse | null | undefined
): DashboardData['cost'] {
  const total = costSummary?.total_cost ?? 0;
  const byProvider = costSummary?.cost_by_provider ?? {};
  const rows = modelUsage?.rows ?? [];
  const todayKey = new Date().toISOString().slice(0, 10);
  const monthKey = todayKey.slice(0, 7);

  const today = rows.reduce((sum, row) => {
    const usageDate = String(row.usage_date).slice(0, 10);
    return usageDate === todayKey ? sum + row.total_cost_usd : sum;
  }, 0);
  const thisMonth = rows.reduce((sum, row) => {
    const usageDate = String(row.usage_date).slice(0, 7);
    return usageDate === monthKey ? sum + row.total_cost_usd : sum;
  }, 0);

  return {
    total,
    today,
    thisMonth: thisMonth > 0 ? thisMonth : total,
    byProvider,
  };
}

export const useDashboardData = () => {
  const healthQuery = useQuery({
    queryKey: queryKeys.allHealth,
    queryFn: () => apiClient.getAllHealth(),
    staleTime: 10_000,
  });
  const costQuery = useQuery({
    queryKey: queryKeys.costSummary,
    queryFn: () => runtimeClient.getCostSummary(),
    staleTime: 60_000,
  });
  const modelUsageQuery = useQuery({
    queryKey: queryKeys.observabilityModelUsage,
    queryFn: () => apiClient.getModelUsage(),
    staleTime: 15_000,
  });
  const metricsQuery = useQuery({
    queryKey: queryKeys.observabilityMetrics,
    queryFn: () => apiClient.getPrometheusMetrics(),
    staleTime: 15_000,
  });
  const cost = toDashboardCost(costQuery.data, modelUsageQuery.data ?? null);

  const dashboard = useMemo<DashboardData>(() => {
    const health = healthQuery.data;

    if (!health) {
      return {
        cost: cost ?? zeroCost,
        backend: defaultService,
        vectorStore: defaultService,
        mcp: defaultService,
        rag: defaultService,
        sandbox: defaultService,
        observability: defaultObservability,
      };
    }

    const services = health.components || health.services || {};

    const metricsPreview = (metricsQuery.data || '')
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .slice(0, 8)
      .join('\n');

    return {
      cost: cost ?? zeroCost,
      backend: toServiceStatus(services['api']),
      vectorStore: toServiceStatus(services['vector_store']),
      mcp: toServiceStatus(services['mcp']),
      rag: toServiceStatus(services['rag']),
      sandbox: toServiceStatus(services['sandbox']),
      observability: {
        modelUsage: modelUsageQuery.data ?? null,
        metricsPreview,
      },
    };
  }, [cost, healthQuery.data, metricsQuery.data, modelUsageQuery.data]);

  return {
    dashboard,
    loading:
      healthQuery.isLoading ||
      costQuery.isLoading ||
      modelUsageQuery.isLoading ||
      metricsQuery.isLoading,
    error:
      healthQuery.error || costQuery.error || modelUsageQuery.error || metricsQuery.error
        ? getUserMessage(
            healthQuery.error || costQuery.error || modelUsageQuery.error || metricsQuery.error
          )
        : null,
    refresh: async () => {
      await Promise.all([
        healthQuery.refetch(),
        costQuery.refetch(),
        modelUsageQuery.refetch(),
        metricsQuery.refetch(),
      ]);
    },
  };
};
