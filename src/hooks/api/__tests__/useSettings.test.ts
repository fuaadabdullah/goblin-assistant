import { renderHook, waitFor } from '@testing-library/react';
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

jest.mock('@/api', () => ({
  apiClient: {
    getProviderSettings: jest.fn(),
    getModelConfigs: jest.fn(),
    getGlobalSettings: jest.fn(),
    updateProvider: jest.fn(),
    updateGlobalSetting: jest.fn(),
  },
}));

jest.mock('../../../lib/query-keys', () => ({
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
import { apiClient } from '@/api';

const mockGetProviders = apiClient.getProviderSettings as jest.Mock;
const mockGetModels = apiClient.getModelConfigs as jest.Mock;
const mockGetGlobal = apiClient.getGlobalSettings as jest.Mock;
const mockUpdateProvider = apiClient.updateProvider as jest.Mock;
const mockUpdateSetting = apiClient.updateGlobalSetting as jest.Mock;

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

describe('useSettings hooks', () => {
  beforeEach(() => jest.clearAllMocks());

  describe('useProviderSettings', () => {
    it('fetches provider settings', async () => {
      const data = [{ name: 'OpenAI', enabled: true }];
      mockGetProviders.mockResolvedValue(data);
      const { result } = renderHook(() => useProviderSettings(), { wrapper });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(data);
    });

    it('handles error', async () => {
      mockGetProviders.mockRejectedValue(new Error('fail'));
      const { result } = renderHook(() => useProviderSettings(), { wrapper });
      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe('useModelConfigs', () => {
    it('fetches model configs', async () => {
      const data = { models: ['gpt-4'] };
      mockGetModels.mockResolvedValue(data);
      const { result } = renderHook(() => useModelConfigs(), { wrapper });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(data);
    });

    it('handles error', async () => {
      mockGetModels.mockRejectedValue(new Error('fail'));
      const { result } = renderHook(() => useModelConfigs(), { wrapper });
      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe('useGlobalSettings', () => {
    it('fetches global settings', async () => {
      const data = { theme: 'dark' };
      mockGetGlobal.mockResolvedValue(data);
      const { result } = renderHook(() => useGlobalSettings(), { wrapper });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(data);
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
