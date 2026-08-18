import { useQuery } from '@tanstack/react-query';
import { api } from '@/api';
import { queryKeys } from '../../../../lib/query-keys';

export interface RoutingAuditRecord {
  event: string;
  request_id: string;
  timestamp: number;
  selected_provider?: string;
  provider_id?: string;
  attempted_providers?: string[];
  model?: string;
  latency_ms?: number;
  cost_usd?: number;
  input_tokens?: number;
  output_tokens?: number;
}

export interface RoutingAuditResponse {
  records: RoutingAuditRecord[];
  count: number;
  current_cost_weight?: number;
}

export interface RoutingStats {
  ewma_latency_ms: number;
  p95_latency_ms: number;
  success_rate: number;
  total_cost_usd: number;
  ewma_tokens_per_sec: number;
}

export interface RoutingProvider {
  id: string;
  name: string;
  type: string;
  routing_stats: RoutingStats;
}

export interface RoutingProvidersResponse {
  providers: Record<string, RoutingProvider>;
}

interface RoutingStatusResponse {
  providers?: Array<{
    id?: string;
    name?: string;
    tier?: string;
    type?: string;
  }>;
  routing_registry?: Record<string, Partial<RoutingStats>>;
}

const emptyStats: RoutingStats = {
  ewma_latency_ms: 0,
  p95_latency_ms: 0,
  success_rate: 1,
  total_cost_usd: 0,
  ewma_tokens_per_sec: 0,
};

function normalizeStats(stats?: Partial<RoutingStats>): RoutingStats {
  const ewmaLatencyMs = Number(stats?.ewma_latency_ms) || 0;

  return {
    ewma_latency_ms: ewmaLatencyMs,
    p95_latency_ms: Number(stats?.p95_latency_ms) || ewmaLatencyMs,
    success_rate: Number(stats?.success_rate) || emptyStats.success_rate,
    total_cost_usd: Number(stats?.total_cost_usd) || 0,
    ewma_tokens_per_sec: Number(stats?.ewma_tokens_per_sec) || 0,
  };
}

async function fetchRoutingProviders(): Promise<RoutingProvidersResponse> {
  const response = await api.get<RoutingStatusResponse>('/routing/status');
  const status = response.data;
  const registry = status.routing_registry ?? {};
  const providers: Record<string, RoutingProvider> = {};

  for (const provider of status.providers ?? []) {
    const id = typeof provider.id === 'string' ? provider.id : '';
    if (!id) continue;

    providers[id] = {
      id,
      name: provider.name ?? id,
      type: provider.tier ?? provider.type ?? 'unknown',
      routing_stats: normalizeStats(registry[id]),
    };
  }

  return { providers };
}

export function useRoutingAudit(limit = 200) {
  return useQuery({
    queryKey: queryKeys.routingAudit(limit),
    queryFn: async () => {
      const response = await api.get<RoutingAuditResponse>(`/routing/audit?limit=${limit}`);
      return response.data;
    },
    refetchInterval: 10_000,
  });
}

export function useRoutingProviders() {
  return useQuery({
    queryKey: queryKeys.routingProviderStatus,
    queryFn: fetchRoutingProviders,
    refetchInterval: 30_000,
  });
}
