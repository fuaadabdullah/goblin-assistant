import { renderHook, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

const mockTestConnection = vi
  .fn()
  .mockResolvedValue({ success: true, message: 'OK', latency: 100 });
const mockTestPrompt = vi
  .fn()
  .mockResolvedValue({ success: true, message: 'Reply', latency: 200, response: 'hello' });
const mockSetPriority = vi.fn().mockResolvedValue({});
const mockReorder = vi.fn().mockResolvedValue({});
vi.mock('../../api', () => ({
  providersAdminApi: {
    testProviderConnection: (...args: unknown[]) => mockTestConnection(...args),
    testProviderWithPrompt: (...args: unknown[]) => mockTestPrompt(...args),
    setProviderPriority: (...args: unknown[]) => mockSetPriority(...args),
    reorderProviders: (...args: unknown[]) => mockReorder(...args),
  },
}));
vi.mock('@/lib/query-keys', () => ({
  queryKeys: { providerSettings: ['providers'] },
}));

import { useProviderMutations } from '../useProviderMutations';
import { formatProviderTestMessage } from '../useProviderMutations';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

const mockProvider = {
  id: 'p1',
  name: 'openai',
  enabled: true,
  configured: true,
  priority: 1,
  base_url: '',
  models: [],
};

describe('useProviderMutations', () => {
  beforeEach(() => vi.clearAllMocks());

  it('returns expected properties', () => {
    const { result } = renderHook(() => useProviderMutations(), { wrapper });
    expect(result.current).toHaveProperty('quickTest');
    expect(result.current).toHaveProperty('promptTest');
    expect(result.current).toHaveProperty('setPriority');
    expect(result.current).toHaveProperty('reorderProviders');
    expect(result.current).toHaveProperty('testing');
    expect(result.current).toHaveProperty('testResult');
  });

  it('quickTest calls provider adapter', async () => {
    const { result } = renderHook(() => useProviderMutations(), { wrapper });
    await act(async () => {
      await result.current.quickTest(mockProvider as never);
    });
    expect(mockTestConnection).toHaveBeenCalledWith('p1');
  });

  it('setPriority calls provider adapter', async () => {
    const { result } = renderHook(() => useProviderMutations(), { wrapper });
    await act(async () => {
      await result.current.setPriority(1, 1);
    });
    expect(mockSetPriority).toHaveBeenCalledWith(1, 1, undefined);
  });

  it('reorderProviders calls provider adapter', async () => {
    const { result } = renderHook(() => useProviderMutations(), { wrapper });
    await act(async () => {
      await result.current.reorderProviders([
        { id: 1, name: 'a' },
        { id: 2, name: 'b' },
      ] as never[]);
    });
    expect(mockReorder).toHaveBeenCalledWith([1, 2]);
  });

  it('testing state reflects current test', async () => {
    const { result } = renderHook(() => useProviderMutations(), { wrapper });
    expect(result.current.testing).toBeNull();
  });

  it('preserves non-Error test failures in the formatter', () => {
    expect(formatProviderTestMessage('provider offline')).toBe('provider offline');
  });
});
