import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api';
import { queryKeys } from '../lib/query-keys';

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
  chroma: ServiceStatus;
  mcp: ServiceStatus;
  rag: ServiceStatus;
  sandbox: ServiceStatus;
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

const defaultCostData = {
  total: 0.24,
  today: 0.02,
  thisMonth: 0.24,
  byProvider: { openai: 0.12, anthropic: 0.08, local: 0.04 },
};

export const useDashboardData = () => {
  const healthQuery = useQuery({
    queryKey: queryKeys.allHealth,
    queryFn: () => apiClient.getAllHealth(),
    staleTime: 10_000,
  });

  const dashboard = useMemo<DashboardData>(() => {
    const health = healthQuery.data;

    if (!health) {
      return {
        cost: defaultCostData,
        backend: defaultService,
        chroma: defaultService,
        mcp: defaultService,
        rag: defaultService,
        sandbox: defaultService,
      };
    }

    const services = health.components || health.services || {};

    return {
      cost: defaultCostData,
      backend: toServiceStatus(services.api),
      chroma: toServiceStatus(services.chroma),
      mcp: toServiceStatus(services.mcp),
      rag: toServiceStatus(services.rag),
      sandbox: toServiceStatus(services.sandbox),
    };
  }, [healthQuery.data]);

  return {
    dashboard,
    loading: healthQuery.isLoading,
    error: healthQuery.error instanceof Error ? healthQuery.error.message : null,
    refresh: healthQuery.refetch,
  };
};
