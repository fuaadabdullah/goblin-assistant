/**
 * Canonical React Query keys for consistent cache management.
 *
 * Keep all query keys defined here (single source of truth).
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
  chatConversation: (conversationId: string) =>
    ['chat', 'conversation', conversationId] as const,

  // Search
  collections: ['search', 'collections'] as const,
  searchResults: (collection: string, query: string, limit = 8) =>
    ['search', 'results', collection, query, limit] as const,

  // Settings
  providers: ['settings', 'providers'] as const,
  credentials: ['settings', 'credentials'] as const,
  modelConfigs: ['settings', 'models'] as const,
  globalSettings: ['settings', 'global'] as const,

  // Auth
  authValidate: ['auth', 'validate'] as const,

  // Routing
  routingProviders: (capability?: string) =>
    capability ? ['routing', 'providers', capability] as const : ['routing', 'providers'] as const,
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
