import { useCallback, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../../api/apiClient';
import type { ProviderConfig } from '../../../../hooks/api/useSettings';
import { queryKeys } from '../../../../lib/queryClient';

export interface TestResult {
  success: boolean;
  message: string;
  latency: number;
  response?: string;
  model_used?: string;
}

export type ProviderRole = 'primary' | 'fallback';

export const useProviderMutations = () => {
  const queryClient = useQueryClient();
  const [testing, setTesting] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<TestResult | null>(null);

  const quickTestMutation = useMutation({
    mutationFn: async (provider: ProviderConfig): Promise<TestResult> => {
      if (!provider.id) {
        return {
          success: false,
          message: 'Provider is missing an id.',
          latency: 0,
        };
      }

      const result = (await apiClient.testProviderConnection(provider.id)) as any;
      return {
        success: Boolean(result?.success),
        message: result?.message ?? 'Connection test completed.',
        latency: Number(result?.latency) || 0,
      };
    },
    onMutate: provider => {
      setTesting(provider.name);
      setTestResult(null);
    },
    onSuccess: result => setTestResult(result),
    onError: error => {
      setTestResult({
        success: false,
        message: error instanceof Error ? error.message : 'Connection test failed',
        latency: 0,
      });
    },
    onSettled: () => setTesting(null),
  });

  const promptTestMutation = useMutation({
    mutationFn: async ({
      provider,
      prompt,
    }: {
      provider: ProviderConfig;
      prompt: string;
    }): Promise<TestResult> => {
      if (!provider.id) {
        return {
          success: false,
          message: 'Provider is missing an id.',
          latency: 0,
        };
      }

      const result = (await apiClient.testProviderWithPrompt(provider.id, prompt)) as any;
      return {
        success: Boolean(result?.success),
        message: result?.message ?? 'Prompt test completed.',
        latency: Number(result?.latency) || 0,
        response: typeof result?.response === 'string' ? result.response : undefined,
        model_used: typeof result?.model_used === 'string' ? result.model_used : undefined,
      };
    },
    onMutate: ({ provider }) => {
      setTesting(provider.name);
      setTestResult(null);
    },
    onSuccess: result => setTestResult(result),
    onError: error => {
      setTestResult({
        success: false,
        message: error instanceof Error ? error.message : 'Test failed',
        latency: 0,
      });
    },
    onSettled: () => setTesting(null),
  });

  const setPriorityMutation = useMutation({
    mutationFn: async ({
      providerId,
      priority,
      role,
    }: {
      providerId: number;
      priority: number;
      role?: ProviderRole;
    }) => apiClient.setProviderPriority(providerId, priority, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.providers });
    },
  });

  const reorderMutation = useMutation({
    mutationFn: async (providerIds: number[]) => apiClient.reorderProviders(providerIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.providers });
    },
  });

  const quickTest = useCallback(
    async (provider: ProviderConfig) => {
      await quickTestMutation.mutateAsync(provider);
    },
    [quickTestMutation]
  );

  const promptTest = useCallback(
    async (provider: ProviderConfig, prompt: string) => {
      await promptTestMutation.mutateAsync({ provider, prompt });
    },
    [promptTestMutation]
  );

  const setPriority = useCallback(
    async (providerId: number, priority: number, role?: ProviderRole) => {
      await setPriorityMutation.mutateAsync({ providerId, priority, role });
    },
    [setPriorityMutation]
  );

  const reorderProviders = useCallback(
    async (newOrder: ProviderConfig[]) => {
      const providerIds = newOrder.map(p => p.id).filter((id): id is number => id !== undefined);
      await reorderMutation.mutateAsync(providerIds);
    },
    [reorderMutation]
  );

  return {
    testing,
    testResult,
    setTestResult,
    quickTest,
    promptTest,
    setPriority,
    reorderProviders,
    isReordering: reorderMutation.isPending,
  };
};

