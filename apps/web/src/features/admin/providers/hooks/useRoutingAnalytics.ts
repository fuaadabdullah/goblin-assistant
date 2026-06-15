import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { queryKeys } from '@/lib/query-keys';

interface RoutingStatsEntry {
  ewma_latency_ms: number;
  p95_latency_ms: number;
  success_rate: number;
  total_cost_usd: number;
  ewma_tokens_per_sec: number;
  total_output_tokens: number;
  last_used: number;
}

interface ProviderEntry {
  id: string;
  name: string;
  type: string;
  capabilities: string[];
  models: string[];
  health: any;
  routing_stats: RoutingStatsEntry;
}

interface RoutingProvidersResponse {
  providers: Record<string, ProviderEntry>;
}

interface RoutingAuditRecord {
  event: string;
  request_id: string;
  provider_id?: string;
  model?: string;
  latency_ms?: number;
  cost_usd?: number;
  input_tokens?: number;
  output_tokens?: number;
  timestamp: number;
  candidates?: string[];
  attempted_providers?: string[];
  selected_provider?: string;
}

interface RoutingAuditResponse {
  records: RoutingAuditRecord[];
  count: number;
  current_cost_weight: number;
}

export function useRoutingProviders() {
  return useQuery({
    queryKey: queryKeys.routingAnalytics,
    queryFn: async (): Promise<RoutingProvidersResponse> => {
      const response = await apiClient.get('/routing/providers');
      return response.data;
    },
    refetchInterval: 30000,
    staleTime: 25000,
  });
}

export function useRoutingAudit(limit = 50) {
  return useQuery({
    queryKey: queryKeys.routingAudit(limit),
    queryFn: async (): Promise<RoutingAuditResponse> => {
      const response = await apiClient.get(`/routing/audit?limit=${limit}`);
      return response.data;
    },
    refetchInterval: 10000,
    staleTime: 8000,
  });
}
