import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useDashboardData } from '../useDashboardData';

jest.mock('@/api', () => ({
  apiClient: {
    getAllHealth: jest.fn().mockResolvedValue({
      services: {
        api: { status: 'healthy', latency: 50 },
        chroma: { status: 'healthy', latency: 100 },
      },
    }),
  },
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
});
