import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/apiClient';
import { queryKeys } from '../../lib/queryClient';

/**
 * Hook to fetch system health status with live updates
 */
export const useHealth = (refetchInterval?: number) => {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: () => apiClient.getAllHealth(),
    refetchInterval: refetchInterval || 10000, // Refetch every 10s by default
    staleTime: 5000, // Consider stale after 5s
  });
};

/**
 * Hook to fetch streaming health
 */
export const useStreamingHealth = (refetchInterval?: number) => {
  return useQuery({
    queryKey: queryKeys.streamingHealth,
    queryFn: () => apiClient.getStreamingHealth(),
    refetchInterval: refetchInterval || 15000,
  });
};

/**
 * Hook to fetch routing health
 */
export const useRoutingHealth = (refetchInterval?: number) => {
  return useQuery({
    queryKey: queryKeys.routingHealth,
    queryFn: () => apiClient.getRoutingHealth(),
    refetchInterval: refetchInterval || 15000,
  });
};
