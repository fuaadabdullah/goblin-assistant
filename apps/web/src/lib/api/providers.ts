import {
  ProviderUpdatePayload,
  getBackend,
  getFrontend,
  patchBackend,
  postBackend,
} from './shared';

export const providersMethods = {
  async getProviderSettings() {
    return getBackend('/providers');
  },

  async getModelConfigs() {
    return getFrontend('/api/models');
  },

  async getGlobalSettings() {
    return getBackend('/settings');
  },

  async updateProvider(providerId: string | number, provider: ProviderUpdatePayload) {
    return patchBackend(`/providers/${providerId}`, provider);
  },

  async updateGlobalSetting(key: string, value: unknown) {
    return patchBackend(`/settings/${encodeURIComponent(key)}`, { value });
  },

  async setProviderPriority(providerId: number, priority: number, role?: string) {
    return postBackend(`/providers/${providerId}/priority`, { priority, role });
  },

  async reorderProviders(providerIds: number[]) {
    return postBackend('/providers/reorder', { providerIds });
  },

  async testProviderConnection(providerId: number | string) {
    return postBackend(`/providers/${providerId}/test`);
  },

  async testProviderWithPrompt(providerId: number | string, prompt: string) {
    return postBackend(`/providers/${providerId}/test-prompt`, { prompt });
  },
};
