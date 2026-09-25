import { getBackend } from './shared';

export interface RetrievedItem {
  source: string;
  source_id: string | null;
  content: string;
  relevance_score: number;
  token_count: number;
  rank: number;
  truncated: boolean;
  metadata: Record<string, unknown>;
}

export interface RetrievalTrace {
  request_id: string;
  user_id: string | null;
  timestamp: string;
  model_selected: string;
  token_budget: number;
  total_tokens_used: number;
  items_retrieved: RetrievedItem[];
  tier_breakdown: Record<string, Record<string, number>>;
  context_hash: string;
  context_snapshot: string;
  retrieval_time_ms: number;
  truncation_events: Array<Record<string, unknown>>;
  error: string | null;
}

export interface RetrievalHistoryResponse {
  traces: RetrievalTrace[];
  summary: {
    total_traces: number;
    avg_retrieval_time: number;
    avg_tokens_used: number;
    error_count: number;
    truncation_count: number;
  };
}

export const retrievalDebugMethods = {
  async getRetrievalHistory(limit = 50): Promise<RetrievalHistoryResponse> {
    return getBackend<RetrievalHistoryResponse>(`/api/v1/debug/retrieval/history?limit=${limit}`);
  },

  async getRetrievalTrace(requestId: string): Promise<RetrievalTrace> {
    return getBackend<RetrievalTrace>(
      `/api/v1/debug/retrieval/trace/${encodeURIComponent(requestId)}`
    );
  },
};
