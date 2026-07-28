'use client';

import { useState, useCallback } from 'react';
import { useHealthCheck } from '@/hooks/useHealthCheck';
import { apiClient } from '@/lib/api';

interface HealthCheckResult {
  status: string;
  [key: string]: unknown;
}

export const useEndpointTests = () => {
  const health = useHealthCheck();
  const [chatTestResult, setTestResult] = useState<HealthCheckResult | null>(null);
  const [chatError, setError] = useState<string | null>(null);

  const handleFetchConversations = useCallback(async () => {
    setError(null);
    setTestResult(null);
    try {
      const response = await apiClient.listConversations();
      setTestResult(response as unknown as HealthCheckResult);
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
    }
  }, []);

  const handleValidateToken = useCallback(async () => {
    setError(null);
    setTestResult(null);
    try {
      // Token will be validated through the API client
      const response = await apiClient.validateToken();
      setTestResult(response as unknown as HealthCheckResult);
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
    }
  }, []);

  const handleAuthLogout = useCallback(async () => {
    setError(null);
    try {
      await apiClient.logout();
      setTestResult({ status: 'logged_out' });
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
    }
  }, []);

  return {
    health,
    chatTestResult,
    chatError,
    handleFetchConversations,
    handleValidateToken,
    handleAuthLogout,
  };
};
