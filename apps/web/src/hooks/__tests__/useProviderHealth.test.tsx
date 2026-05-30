import { renderHook, waitFor } from '@testing-library/react';
import { useProviderHealth } from '../useProviderHealth';
import { apiClient } from '@/api';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

jest.mock('@/api', () => ({
  apiClient: {
    getModelConfigs: jest.fn(),
  },
}));

const mockGetModelConfigs = apiClient.getModelConfigs as jest.Mock;

function wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe('useProviderHealth', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('returns undefined initially while loading', () => {
    mockGetModelConfigs.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useProviderHealth(), { wrapper });
    expect(result.current.loadingProviders).toBe(true);
  });

  it('returns provider health data when loaded', async () => {
    const mockData = {
      providers: [
        { id: 'openai', health: 'healthy', is_selectable: true },
        { id: 'anthropic', health: 'healthy', is_selectable: true },
      ],
      models: [],
    };
    mockGetModelConfigs.mockResolvedValue(mockData);

    const { result } = renderHook(() => useProviderHealth(), { wrapper });

    await waitFor(() => {
      expect(result.current.loadingProviders).toBe(false);
    });

    expect(result.current.providers).toEqual(expect.arrayContaining(['openai', 'anthropic']));
  });

  it('handles errors gracefully', async () => {
    mockGetModelConfigs.mockRejectedValue(new Error('API error'));

    const { result } = renderHook(() => useProviderHealth(), { wrapper });

    await waitFor(() => {
      expect(result.current.providerError).toBe('API error');
    }, { timeout: 4000 });

    await waitFor(() => {
      expect(result.current.loadingProviders).toBe(false);
    });

    expect(result.current.providerError).toBeDefined();
  });

  it('normalizes health status to lowercase', async () => {
    const mockData = {
      providers: [{ id: 'openai', health: 'HEALTHY', is_selectable: true }],
      models: [],
    };
    mockGetModelConfigs.mockResolvedValue(mockData);

    const { result } = renderHook(() => useProviderHealth(), { wrapper });

    await waitFor(() => {
      expect(result.current.loadingProviders).toBe(false);
    });

    const openaiConfig = result.current.providerConfigs.get('openai');
    expect(openaiConfig?.health).toBe('healthy');
  });
});
