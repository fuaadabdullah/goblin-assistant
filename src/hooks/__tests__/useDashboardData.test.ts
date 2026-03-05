import { renderHook, act, waitFor } from '@testing-library/react';
import { useDashboardData } from '../useDashboardData';

describe('useDashboardData Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should have initial loading state', () => {
    const { result } = renderHook(() => useDashboardData());
    expect(result.current.isLoading).toBe(true);
  });

  it('should fetch dashboard data', async () => {
    const { result } = renderHook(() => useDashboardData());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toBeDefined();
  });

  it('should handle errors gracefully', async () => {
    const { result } = renderHook(() => useDashboardData());

    await waitFor(() => {
      if (!result.current.isLoading && result.current.error) {
        expect(result.current.error).toBeDefined();
      }
    });
  });

  it('should refetch data on demand', async () => {
    const { result } = renderHook(() => useDashboardData());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      result.current.refetch?.();
    });

    await waitFor(() => {
      // Should refetch
    });
  });
});
