import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api';
import { queryKeys } from '../../lib/query-keys';

/**
 * Hook to fetch provider settings
 */
// Types for provider settings
export interface ProviderConfig {
  id?: number;
  name: string;
  enabled: boolean;
  priority?: number;
  weight?: number;
  api_key?: string;
  base_url?: string;
  models?: string[];
}

export const useProviderSettings = () => {
  return useQuery<ProviderConfig[]>({
    queryKey: queryKeys.providers,
    queryFn: async () => (await apiClient.getProviderSettings()) as ProviderConfig[],
  });
};

/**
 * Hook to fetch model configurations
 */
export const useModelConfigs = () => {
  return useQuery({
    queryKey: queryKeys.modelConfigs,
    queryFn: () => apiClient.getModelConfigs(),
  });
};

/**
 * Hook to fetch global settings
 */
export const useGlobalSettings = () => {
  return useQuery({
    queryKey: queryKeys.globalSettings,
    queryFn: () => apiClient.getGlobalSettings(),
  });
};

/**
 * Hook to update a provider
 */
export const useUpdateProvider = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ providerId, provider }: { providerId: number; provider: Partial<ProviderConfig> }) =>
      apiClient.updateProvider(providerId, provider),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.providers });
    },
  });
};

/**
 * Hook to update global setting
 */
export const useUpdateGlobalSetting = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      apiClient.updateGlobalSetting(key, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.globalSettings });
    },
  });
};
