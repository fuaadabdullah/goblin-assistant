import { frontendHttp, getFrontend } from './shared';
import type { ModelUsageRollupResponse, ModelUsageRollup } from '@/types/api';

export const observabilityMethods = {
  async getModelUsage(provider?: string, model?: string): Promise<ModelUsageRollupResponse> {
    const params = new URLSearchParams();
    if (provider) params.set('provider', provider);
    if (model) params.set('model', model);
    const query = params.toString();
    const url = query ? `/api/debug/model-usage?${query}` : '/api/debug/model-usage';
    return getFrontend<ModelUsageRollupResponse>(url);
  },

  async getPrometheusMetrics(): Promise<string> {
    const response = await frontendHttp.get<string>('/api/metrics', {
      responseType: 'text',
      transformResponse: [(data) => data],
    });
    return typeof response.data === 'string' ? response.data : String(response.data ?? '');
  },
};

export type { ModelUsageRollup, ModelUsageRollupResponse };
