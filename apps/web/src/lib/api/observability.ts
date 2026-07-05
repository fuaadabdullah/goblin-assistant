import { backendHttp, V1_API_PREFIX, getBackend } from './shared';
import type {
  ModelUsageRollupResponse,
  ModelUsageRollup,
} from '@/types/api';

export const observabilityMethods = {
  async getModelUsage(provider?: string, model?: string): Promise<ModelUsageRollupResponse> {
    const params = new URLSearchParams();
    if (provider) params.set('provider', provider);
    if (model) params.set('model', model);
    const query = params.toString();
    const url = query
      ? `${V1_API_PREFIX}/debug/model-usage?${query}`
      : `${V1_API_PREFIX}/debug/model-usage`;
    return getBackend<ModelUsageRollupResponse>(url);
  },

  async getPrometheusMetrics(): Promise<string> {
    const response = await backendHttp.get<string>('/metrics', {
      responseType: 'text',
      transformResponse: [(data) => data],
    });
    return typeof response.data === 'string' ? response.data : String(response.data ?? '');
  },
};

export type { ModelUsageRollup, ModelUsageRollupResponse };
