// lib/services/provider-service.ts
import { apiClient } from './api-client';
import type { ProviderConfig, ProviderHealth } from '../types';

export class ProviderService {
  // Get all providers
  async getProviders(): Promise<ProviderConfig[]> {
    const response = await apiClient.get<{ providers: ProviderConfig[] }>('/providers');

    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to get providers');
    }

    return response.data.providers;
  }

  // Get provider health status
  async getProviderHealth(): Promise<ProviderHealth[]> {
    const response = await apiClient.get<{ health: ProviderHealth[] }>('/providers/health');

    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to get provider health');
    }

    return response.data.health;
  }

  // Update provider configuration
  async updateProvider(providerId: string, config: Partial<ProviderConfig>): Promise<ProviderConfig> {
    const response = await apiClient.put<ProviderConfig>(`/providers/${providerId}`, config);

    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to update provider');
    }

    return response.data;
  }

  // Test provider connection
  async testProvider(providerId: string): Promise<{ success: boolean; latency?: number; error?: string }> {
    const response = await apiClient.post<{ success: boolean; latency?: number; error?: string }>(
      `/providers/${providerId}/test`
    );

    if (!response.success || !response.data) {
      return {
        success: false,
        error: response.error?.message || 'Test failed',
      };
    }

    return response.data;
  }

  // Get provider models
  async getProviderModels(providerId: string): Promise<string[]> {
    const response = await apiClient.get<{ models: string[] }>(`/providers/${providerId}/models`);

    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to get provider models');
    }

    return response.data.models;
  }

  // Refresh provider health
  async refreshHealth(): Promise<ProviderHealth[]> {
    const response = await apiClient.post<{ health: ProviderHealth[] }>('/providers/health/refresh');

    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to refresh health');
    }

    return response.data.health;
  }
}

// Export singleton instance
export const providerService = new ProviderService();
