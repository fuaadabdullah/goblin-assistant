import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { queryKeys } from '@/lib/query-keys';

export const useHealthCheck = () => {
  return useQuery({
    queryKey: queryKeys.allHealth,
    queryFn: () => apiClient.getAllHealth(),
    refetchInterval: 5000, // Refetch every 5 seconds
    staleTime: 2000,
  });
};
