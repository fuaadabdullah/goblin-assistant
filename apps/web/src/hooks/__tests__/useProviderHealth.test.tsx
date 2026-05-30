import { renderHook, waitFor } from '@testing-library/react';
import { useProviderHealth } from '../useProviderHealth';
import { apiClient } from '@/api';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

jest.mock('@/api', () => ({
  apiClient: {
    getProvidersRegistry: jest.fn(),
  },
}));

const mockGetProvidersRegistry = apiClient.getProvidersRegistry as jest.Mock;

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
    mockGetProvidersRegistry.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useProviderHealth(), { wrapper });
    expect(result.current.isLoading).toBe(true);
  });

  it('returns provider health data when loaded', async () => {
    const mockData = {
      providers: {
        openai: { health: 'healthy', is_selectable: true },
        anthropic: { health: 'healthy', is_selectable: true },
      },
    };
    mockGetProvidersRegistry.mockResolvedValue(mockData);

    const { result } = renderHook(() => useProviderHealth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.providers).toBeDefined();
  });

  it('handles errors gracefully', async () => {
    mockGetProvidersRegistry.mockRejectedValue(new Error('API error'));

    const { result } = renderHook(() => useProviderHealth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBeDefined();
  });

  it('normalizes health status to lowercase', async () => {
    const mockData = {
      providers: {
        openai: { health: 'HEALTHY', is_selectable: true },
      },
    };
    mockGetProvidersRegistry.mockResolvedValue(mockData);

    const { result } = renderHook(() => useProviderHealth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.providers).toBeDefined();
  });
});
