import { apiClient } from '@/lib/api';
import type { ProviderRole } from '../hooks/useProviderMutations';
import type { ProviderTestResponse } from '../../../../types/api';

export const providersAdminApi = {
  testProviderConnection(providerId: number | string): Promise<ProviderTestResponse> {
    return apiClient.testProviderConnection(providerId) as Promise<ProviderTestResponse>;
  },

  testProviderWithPrompt(
    providerId: number | string,
    prompt: string
  ): Promise<ProviderTestResponse> {
    return apiClient.testProviderWithPrompt(providerId, prompt) as Promise<ProviderTestResponse>;
  },

  setProviderPriority(providerId: number, priority: number, role?: ProviderRole) {
    return apiClient.setProviderPriority(providerId, priority, role);
  },

  reorderProviders(providerIds: number[]) {
    return apiClient.reorderProviders(providerIds);
  },
};
