import { useCallback, useState } from 'react';

// Sentry v8 re-exports core functions from @sentry/browser.
// When @sentry/browser types aren't resolved (e.g. missing transitive dep),
// import the namespace and cast to access the runtime-available core APIs.
const Sentry: {
  captureException: (error: unknown) => string;
  captureMessage: (message: string, level?: string) => string;
  addBreadcrumb: (breadcrumb: { message?: string; category?: string; level?: string }) => void;
} = require('@sentry/react');

export type ErrorTestStatus = 'success' | 'failed';

export interface ErrorTestResult {
  id: string;
  label: string;
  status: ErrorTestStatus;
  message?: string;
  timestamp: string;
}

const createId = () => `${Date.now()}-${Math.random().toString(16).slice(2)}`;

export const useErrorTesting = (onSuccess?: (title: string, message?: string) => void) => {
  const [results, setResults] = useState<ErrorTestResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const addResult = useCallback((label: string, status: ErrorTestStatus, message?: string) => {
    setResults(prev => [
      ...prev,
      {
        id: createId(),
        label,
        status,
        message,
        timestamp: new Date().toISOString(),
      },
    ]);
  }, []);

  const wrapTest = useCallback(
    async (label: string, fn: () => void | Promise<void>) => {
      try {
        await fn();
        addResult(label, 'success');
        onSuccess?.('Test completed', label);
      } catch (error) {
        addResult(label, 'failed', error instanceof Error ? error.message : String(error));
      }
    },
    [addResult, onSuccess]
  );

  const testJavaScriptError = () =>
    wrapTest('JavaScript Error', () => {
      throw new Error('Test JavaScript error');
    });

  const testAsyncError = () =>
    wrapTest('Async Error', async () => {
      await Promise.reject(new Error('Test async error'));
    });

  const testNetworkError = () =>
    wrapTest('Network Error', async () => {
      await fetch('/__invalid__endpoint__');
    });

  const testUnhandledPromiseRejection = () =>
    wrapTest('Unhandled Promise Rejection', () => {
      void Promise.reject(new Error('Unhandled rejection'));
    });

  const testTypeError = () =>
    wrapTest('Type Error', () => {
      const value: any = null;
      value.trim();
    });

  const testCustomError = () =>
    wrapTest('Custom Error', () => {
      throw new Error('Custom error for monitoring');
    });

  const testSentryError = () =>
    wrapTest('Sentry Error', () => {
      Sentry.captureException(new Error('Sentry test error'));
    });

  const testSentryMessage = () =>
    wrapTest('Sentry Message', () => {
      Sentry.captureMessage('Sentry test message', 'info');
    });

  const testSentryBreadcrumb = () =>
    wrapTest('Sentry Breadcrumb', () => {
      Sentry.addBreadcrumb({
        message: 'Sentry breadcrumb',
        category: 'test',
        level: 'info',
      });
      Sentry.captureMessage('Sentry breadcrumb test message', 'info');
    });

  const runAllTests = async () => {
    setIsLoading(true);
    await testJavaScriptError();
    await testTypeError();
    await testCustomError();
    await testAsyncError();
    await testNetworkError();
    await testUnhandledPromiseRejection();
    await testSentryError();
    await testSentryMessage();
    await testSentryBreadcrumb();
    setIsLoading(false);
  };

  const clearResults = () => setResults([]);

  return {
    isLoading,
    results,
    testJavaScriptError,
    testAsyncError,
    testNetworkError,
    testUnhandledPromiseRejection,
    testTypeError,
    testCustomError,
    testSentryError,
    testSentryMessage,
    testSentryBreadcrumb,
    runAllTests,
    clearResults,
  };
};
