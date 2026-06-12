import { renderHook, waitFor } from '@testing-library/react';
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('@/lib/api', () => ({
  apiClient: {
    getProviderSettings: vi.fn(),
    getModelConfigs: vi.fn(),
    getGlobalSettings: vi.fn(),
    updateProvider: vi.fn(),
    updateGlobalSetting: vi.fn(),
  },
}));

vi.mock('../../../lib/query-keys', () => ({
  queryKeys: {
    providers: ['providers'],
    modelConfigs: ['modelConfigs'],
    globalSettings: ['globalSettings'],
  },
}));

import {
  useProviderSettings,
  useModelConfigs,
  useGlobalSettings,
  useUpdateProvider,
  useUpdateGlobalSetting,
} from '../useSettings';
import { apiClient } from '@/lib/api';

const mockGetProviders = apiClient.getProviderSettings as vi.Mock;
const mockGetModels = apiClient.getModelConfigs as vi.Mock;
const mockGetGlobal = apiClient.getGlobalSettings as vi.Mock;
const mockUpdateProvider = apiClient.updateProvider as vi.Mock;
const mockUpdateSetting = apiClient.updateGlobalSetting as vi.Mock;

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

describe('useSettings hooks', () => {
  beforeEach(() => vi.clearAllMocks());

  describe('useProviderSettings', () => {
    it('fetches provider settings', async () => {
      const providerSettings = [{ name: 'OpenAI', enabled: true }];
      mockGetProviders.mockResolvedValue(providerSettings);
      const { result } = renderHook(() => useProviderSettings(), { wrapper });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(providerSettings);
    });

    it('handles error', async () => {
      mockGetProviders.mockRejectedValue(new Error('fail'));
      const { result } = renderHook(() => useProviderSettings(), { wrapper });
      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe('useModelConfigs', () => {
    it('fetches model configs', async () => {
      const modelConfigs = { models: ['gpt-4'] };
      mockGetModels.mockResolvedValue(modelConfigs);
      const { result } = renderHook(() => useModelConfigs(), { wrapper });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(modelConfigs);
    });

    it('handles error', async () => {
      mockGetModels.mockRejectedValue(new Error('fail'));
      const { result } = renderHook(() => useModelConfigs(), { wrapper });
      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe('useGlobalSettings', () => {
    it('fetches global settings', async () => {
      const globalSettings = { theme: 'dark' };
      mockGetGlobal.mockResolvedValue(globalSettings);
      const { result } = renderHook(() => useGlobalSettings(), { wrapper });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(globalSettings);
    });
  });

  describe('useUpdateProvider', () => {
    it('calls updateProvider', async () => {
      mockUpdateProvider.mockResolvedValue({ success: true });
      mockGetProviders.mockResolvedValue([]);
      const { result } = renderHook(() => useUpdateProvider(), { wrapper });
      result.current.mutate({ providerId: 1, provider: { enabled: false } });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(mockUpdateProvider).toHaveBeenCalledWith(1, { enabled: false });
    });
  });

  describe('useUpdateGlobalSetting', () => {
    it('calls updateGlobalSetting', async () => {
      mockUpdateSetting.mockResolvedValue({ success: true });
      mockGetGlobal.mockResolvedValue({});
      const { result } = renderHook(() => useUpdateGlobalSetting(), { wrapper });
      result.current.mutate({ key: 'theme', value: 'light' });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(mockUpdateSetting).toHaveBeenCalledWith('theme', 'light');
    });
  });
});
