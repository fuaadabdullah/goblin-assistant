// hooks/useApi.ts
'use client';

import { useCallback, useState } from 'react';
import { apiClient } from '../../lib/services';
import type { ApiResponse } from '../../lib/types';

export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async <T,>(
    operation: () => Promise<ApiResponse<T>>,
    options?: {
      onSuccess?: (data: T) => void;
      onError?: (error: string) => void;
      showError?: boolean;
    }
  ): Promise<ApiResponse<T>> => {
    setLoading(true);
    setError(null);

    try {
      const response = await operation();

      if (response.success && response.data && options?.onSuccess) {
        options.onSuccess(response.data);
      }

      if (!response.success && response.error) {
        const errorMessage = response.error.message;
        setError(errorMessage);

        if (options?.showError !== false && options?.onError) {
          options.onError(errorMessage);
        }
      }

      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred';
      setError(errorMessage);

      if (options?.showError !== false && options?.onError) {
        options.onError(errorMessage);
      }

      return {
        success: false,
        error: {
          code: 'UNEXPECTED_ERROR',
          message: errorMessage,
          statusCode: 0,
        },
        meta: {
          timestamp: new Date().toISOString(),
          requestId: Math.random().toString(36).substring(7),
          version: '1.0',
        },
      };
    } finally {
      setLoading(false);
    }
  }, []);

  const get = useCallback(<T,>(
    endpoint: string,
    params?: Record<string, string>,
    options?: Parameters<typeof execute>[1]
  ) => {
    return execute(() => apiClient.get<T>(endpoint, params), options);
  }, [execute]);

  const post = useCallback(<T,>(
    endpoint: string,
    data?: unknown,
    options?: Parameters<typeof execute>[1]
  ) => {
    return execute(() => apiClient.post<T>(endpoint, data), options);
  }, [execute]);

  const put = useCallback(<T,>(
    endpoint: string,
    data?: unknown,
    options?: Parameters<typeof execute>[1]
  ) => {
    return execute(() => apiClient.put<T>(endpoint, data), options);
  }, [execute]);

  const del = useCallback(<T,>(
    endpoint: string,
    options?: Parameters<typeof execute>[1]
  ) => {
    return execute(() => apiClient.delete<T>(endpoint), options);
  }, [execute]);

  const reset = useCallback(() => {
    setLoading(false);
    setError(null);
  }, []);

  return {
    loading,
    error,
    execute,
    get,
    post,
    put,
    delete: del,
    reset,
  };
}
