import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useDashboardData } from '../useDashboardData';

vi.mock('@/lib/api', () => ({
  apiClient: {
    getAllHealth: vi.fn().mockResolvedValue({
      services: {
        api: { status: 'healthy', latency: 50 },
        chroma: { status: 'healthy', latency: 100 },
      },
    }),
    getModelUsage: vi.fn().mockResolvedValue({
      rows: [],
      summary: { request_count: 0, total_cost_usd: 0, total_latency_ms: 0 },
    }),
    getPrometheusMetrics: vi.fn().mockResolvedValue(''),
  },
}));
vi.mock('@/lib/api/runtimeClient', () => ({
  runtimeClient: {
    getCostSummary: vi.fn().mockResolvedValue({
      total_cost: 0,
      cost_by_provider: {},
      cost_by_model: {},
      requests_by_provider: {},
    }),
  },
}));
vi.mock('@/lib/error/toast', () => ({
  getUserMessage: (error: unknown) => (error instanceof Error ? error.message : String(error)),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe('useDashboardData Hook', () => {
  it('should return dashboard data with defaults', async () => {
    const { result } = renderHook(() => useDashboardData(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.dashboard).toBeDefined();
    expect(result.current.dashboard.cost).toBeDefined();
    expect(result.current.dashboard.backend).toBeDefined();
  });

  it('should have refresh function', () => {
    const { result } = renderHook(() => useDashboardData(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.refresh).toBe('function');
  });

  it('should have null error on success', async () => {
    const { result } = renderHook(() => useDashboardData(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeNull();
  });

  it('maps the real cost summary into dashboard cost state', async () => {
    const { runtimeClient } = await import('@/lib/api/runtimeClient');
    (runtimeClient.getCostSummary as vi.Mock).mockResolvedValueOnce({
      total_cost: 4.5,
      cost_by_provider: { openai: 3.25, anthropic: 1.25 },
      cost_by_model: {},
      requests_by_provider: {},
    });
    const { apiClient } = await import('@/lib/api');
    (apiClient.getModelUsage as vi.Mock).mockResolvedValueOnce({
      rows: [
        {
          usage_date: new Date().toISOString().slice(0, 10),
          provider: 'openai',
          model: 'gpt-4o-mini',
          request_count: 1,
          total_tokens: 100,
          total_cost_usd: 0.75,
          total_latency_ms: 1000,
        },
        {
          usage_date: new Date(Date.now() - 31 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
          provider: 'anthropic',
          model: 'claude',
          request_count: 1,
          total_tokens: 50,
          total_cost_usd: 1.0,
          total_latency_ms: 800,
        },
      ],
      summary: { request_count: 2, total_cost_usd: 1.75, total_latency_ms: 1800 },
    });

    const { result } = renderHook(() => useDashboardData(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.dashboard.cost.total).toBe(4.5);
    expect(result.current.dashboard.cost.byProvider).toEqual({
      openai: 3.25,
      anthropic: 1.25,
    });
    expect(result.current.dashboard.cost.today).toBe(0.75);
    expect(result.current.dashboard.cost.thisMonth).toBe(0.75);
  });

  it('surfaces dashboard load errors as user messages', async () => {
    const { apiClient } = await import('@/lib/api');
    (apiClient.getAllHealth as vi.Mock).mockRejectedValueOnce(new Error('health unavailable'));

    const { result } = renderHook(() => useDashboardData(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.error).toBe('health unavailable');
    });
  });
});
