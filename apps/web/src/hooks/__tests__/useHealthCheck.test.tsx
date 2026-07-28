import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useHealthCheck } from '../useHealthCheck';
import * as api from '@/lib/api';
import { queryKeys } from '@/lib/query-keys';
import { ReactNode } from 'react';

vi.mock('@/lib/api', () => ({
  apiClient: {
    getAllHealth: vi.fn(),
  },
}));

describe('useHealthCheck', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient.clear();
  });

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it('should fetch health status on mount', async () => {
    const mockHealthResponse = {
      status: 'healthy',
      timestamp: '2026-07-03T19:40:00Z',
      version: '0.2.0',
      components: {
        api: { status: 'healthy' },
      },
    };

    vi.mocked(api.apiClient.getAllHealth).mockResolvedValue(mockHealthResponse);

    const { result } = renderHook(() => useHealthCheck(), { wrapper });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockHealthResponse);
    expect(api.apiClient.getAllHealth).toHaveBeenCalled();
  });

  it('should handle errors gracefully', async () => {
    const errorMessage = 'Connection failed';
    vi.mocked(api.apiClient.getAllHealth).mockRejectedValue(new Error(errorMessage));

    const { result } = renderHook(() => useHealthCheck(), { wrapper });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeDefined();
  });

  it('should have correct query configuration', () => {
    vi.mocked(api.apiClient.getAllHealth).mockResolvedValue({
      status: 'healthy',
    });

    const { result } = renderHook(() => useHealthCheck(), { wrapper });

    expect(result.current).toBeDefined();
    const query = queryClient.getQueryCache().find({ queryKey: queryKeys.allHealth });
    expect(query?.options).toMatchObject({
      refetchInterval: 5000,
      staleTime: 2000,
    });
  });
});
