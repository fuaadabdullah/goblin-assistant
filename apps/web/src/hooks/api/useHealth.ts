import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { queryKeys } from '../../lib/query-keys';
import { useProviderStatus } from '../useProviderStatus';

export const useHealth = (refetchInterval?: number) => {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: () => apiClient.getAllHealth(),
    refetchInterval: refetchInterval || 10000,
    staleTime: 5000,
  });
};

export const useStreamingHealth = (refetchInterval?: number) => {
  return useQuery({
    queryKey: queryKeys.streamingHealth,
    queryFn: () => apiClient.getStreamingHealth(),
    refetchInterval: refetchInterval || 15000,
  });
};

/**
 * Routing health derived from Supabase Realtime provider_status rows.
 * Falls back to HTTP polling when Supabase is not configured.
 */
export const useRoutingHealth = (refetchInterval?: number) => {
  const { statuses, isLoading, connected } = useProviderStatus();

  // Derive an overall routing status from the live provider snapshots
  const realtimeData = useMemo(() => {
    const rows = Object.values(statuses);
    if (rows.length === 0) return null;
    const healthy = rows.filter((r) => r.is_healthy).length;
    const total = rows.length;
    const status =
      healthy === total ? 'Healthy' : healthy === 0 ? 'Unhealthy' : 'Degraded';
    return { status, healthy, total, providers: statuses, realtime: true };
  }, [statuses]);

  // Fallback HTTP query — only runs when Realtime is not yet connected
  const fallback = useQuery({
    queryKey: queryKeys.routingHealth,
    queryFn: () => apiClient.getRoutingHealth(),
    refetchInterval: connected ? false : refetchInterval || 15000,
    enabled: !connected,
  });

  if (connected || (!isLoading && realtimeData)) {
    return {
      data: realtimeData,
      isLoading,
      error: null,
      isSuccess: Boolean(realtimeData),
    };
  }
  return fallback;
};
