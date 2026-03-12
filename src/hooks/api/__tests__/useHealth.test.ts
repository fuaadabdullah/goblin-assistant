import { renderHook } from '@testing-library/react';
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

jest.mock('@/api', () => ({
  apiClient: {
    getAllHealth: jest.fn().mockResolvedValue({ status: 'healthy' }),
    getStreamingHealth: jest.fn().mockResolvedValue({ status: 'ok' }),
    getRoutingHealth: jest.fn().mockResolvedValue({ status: 'ok' }),
  },
}));

jest.mock('@/lib/query-keys', () => ({
  queryKeys: {
    health: ['health'],
    streamingHealth: ['streaming-health'],
    routingHealth: ['routing-health'],
  },
}));

import { useHealth, useStreamingHealth, useRoutingHealth } from '../useHealth';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

describe('useHealth', () => {
  it('returns query result', () => {
    const { result } = renderHook(() => useHealth(), { wrapper });
    expect(result.current).toHaveProperty('data');
    expect(result.current).toHaveProperty('isLoading');
  });

  it('accepts custom refetchInterval', () => {
    const { result } = renderHook(() => useHealth(5000), { wrapper });
    expect(result.current).toBeDefined();
  });
});

describe('useStreamingHealth', () => {
  it('returns query result', () => {
    const { result } = renderHook(() => useStreamingHealth(), { wrapper });
    expect(result.current).toHaveProperty('data');
    expect(result.current).toHaveProperty('isLoading');
  });

  it('accepts custom refetchInterval', () => {
    const { result } = renderHook(() => useStreamingHealth(3000), { wrapper });
    expect(result.current).toBeDefined();
  });
});

describe('useRoutingHealth', () => {
  it('returns query result', () => {
    const { result } = renderHook(() => useRoutingHealth(), { wrapper });
    expect(result.current).toHaveProperty('data');
    expect(result.current).toHaveProperty('isLoading');
  });

  it('accepts custom refetchInterval', () => {
    const { result } = renderHook(() => useRoutingHealth(2000), { wrapper });
    expect(result.current).toBeDefined();
  });
});
