import { QueryClient, QueryCache, MutationCache } from '@tanstack/query-core';
import { logError, isRetryable } from './error';
export { queryKeys } from './query-keys';

/**
 * Global React Query configuration
 */
export const createQueryClient = () =>
  new QueryClient({
    queryCache: new QueryCache({
      onError: (error, query) =>
        logError(error, { action: 'query', queryKey: JSON.stringify(query.queryKey) }),
    }),
    mutationCache: new MutationCache({
      onError: (error, _variables, _context, mutation) =>
        logError(error, {
          action: 'mutation',
          mutationKey: JSON.stringify(mutation.options.mutationKey),
        }),
    }),
    defaultOptions: {
      queries: {
        // Only auto-retry server errors (5xx, rate limits, timeouts).
        // Auth failures, 404s, and validation errors are not retried.
        retry: (failureCount, error) => failureCount < 3 && isRetryable(error),
        retryDelay: (attemptIndex: number) => Math.min(500 * 2 ** attemptIndex, 30000),
        staleTime: 5 * 60 * 1000,
        gcTime: 10 * 60 * 1000,
        refetchOnWindowFocus: false,
        refetchOnReconnect: true,
      },
      mutations: {
        retry: (failureCount, error) => failureCount < 1 && isRetryable(error),
        retryDelay: 1000,
      },
    },
  });
