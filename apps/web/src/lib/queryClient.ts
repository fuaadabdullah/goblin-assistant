import { QueryClient } from '@tanstack/query-core';
export { queryKeys } from './query-keys';

/**
 * Global React Query configuration
 */
export const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: 3, // Retry failed requests 3 times
        retryDelay: (attemptIndex: number) => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff
        staleTime: 5 * 60 * 1000, // Data is fresh for 5 minutes
        gcTime: 10 * 60 * 1000, // Cache for 10 minutes (formerly cacheTime)
        refetchOnWindowFocus: false, // Don't refetch on window focus
        refetchOnReconnect: true, // Refetch on reconnect
      },
      mutations: {
        retry: 1, // Retry mutations once
        retryDelay: 1000,
      },
    },
  });

