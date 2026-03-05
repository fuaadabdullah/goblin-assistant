import { useCallback, useEffect, useState } from 'react';
import { apiClient } from '../api/apiClient';

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

export const useDashboardData = () => {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const health = await apiClient.getAllHealth();
      setDashboard(prev => ({
        cost: prev?.cost || {
          total: 0.24,
          today: 0.02,
          thisMonth: 0.24,
          byProvider: { openai: 0.12, anthropic: 0.08, local: 0.04 },
        },
        backend: (health as any)?.services?.api || defaultService,
        chroma: (health as any)?.services?.chroma || defaultService,
        mcp: (health as any)?.services?.mcp || defaultService,
        rag: (health as any)?.services?.rag || defaultService,
        sandbox: (health as any)?.services?.sandbox || defaultService,
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
      if (!dashboard) {
        setDashboard({
          cost: {
            total: 0,
            today: 0,
            thisMonth: 0,
            byProvider: {},
          },
          backend: defaultService,
          chroma: defaultService,
          mcp: defaultService,
          rag: defaultService,
          sandbox: defaultService,
        });
      }
    } finally {
      setLoading(false);
    }
  }, [dashboard]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return {
    dashboard,
    loading,
    error,
    refresh,
  };
};
