import { QueryClient } from '@tanstack/react-query';

/**
 * Global React Query configuration
 */
export const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: 3, // Retry failed requests 3 times
        retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff
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

/**
 * Query keys for consistent cache management
 */
export const queryKeys = {
  // Health
  health: ['health'] as const,
  streamingHealth: ['health', 'streaming'] as const,
  allHealth: ['health', 'all'] as const,

  // Chat
  models: ['chat', 'models'] as const,
  routingInfo: ['chat', 'routing-info'] as const,
  chatThreads: ['chat', 'threads'] as const,

  // Search
  collections: ['search', 'collections'] as const,

  // Settings
  providers: ['settings', 'providers'] as const,
  credentials: ['settings', 'credentials'] as const,
  modelConfigs: ['settings', 'models'] as const,
  globalSettings: ['settings', 'global'] as const,

  // Routing
  routingProviders: (capability?: string) =>
    capability ? ['routing', 'providers', capability] : (['routing', 'providers'] as const),
  routingHealth: ['routing', 'health'] as const,

  // Goblins
  goblins: ['goblins'] as const,
  goblinHistory: (goblinId: string, limit: number) =>
    ['goblins', goblinId, 'history', limit] as const,
  goblinStats: (goblinId: string) => ['goblins', goblinId, 'stats'] as const,

  // RAPTOR
  raptorStatus: ['raptor', 'status'] as const,
  raptorLogs: (limit?: number) => ['raptor', 'logs', limit] as const,

  // Sandbox
  sandboxJobs: ['sandbox', 'jobs'] as const,
  jobLogs: (jobId: string) => ['sandbox', 'jobs', jobId, 'logs'] as const,
  jobArtifacts: (jobId: string) => ['sandbox', 'jobs', jobId, 'artifacts'] as const,
};
