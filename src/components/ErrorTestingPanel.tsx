import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import Alert from './ui/Alert';
import { useToast } from '../contexts/ToastContext';
import { Button } from './ui';
import { useErrorTesting } from '../hooks/useErrorTesting';
import { ErrorTestButtons } from './error-testing/ErrorTestButtons';
import { ErrorTestResults } from './error-testing/ErrorTestResults';

export const ErrorTestingPanel: React.FC = () => {
  const { showSuccess } = useToast();
  const {
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
  } = useErrorTesting(showSuccess);

  return (
    <Card className="w-full max-w-4xl mx-auto">
      <CardHeader>
        <CardTitle>Datadog Error Testing Panel</CardTitle>
        <CardDescription>
          Generate various types of errors to test RUM error tracking. All errors will be
          captured and sent to your configured monitoring dashboard.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Alert message={
            '⚠️ This panel is for testing purposes only. It will intentionally generate errors that should appear in your RUM dashboard.'
        } />

        <ErrorTestButtons
          onJavaScriptError={testJavaScriptError}
          onTypeError={testTypeError}
          onCustomError={testCustomError}
          onAsyncError={testAsyncError}
          onNetworkError={testNetworkError}
          onUnhandledPromiseRejection={testUnhandledPromiseRejection}
          onSentryError={testSentryError}
          onSentryMessage={testSentryMessage}
          onSentryBreadcrumb={testSentryBreadcrumb}
          onRunAll={runAllTests}
          running={isLoading}
        />

        <div className="flex gap-4">
          <Button onClick={() => clearResults()} variant="ghost">
            Clear Results
          </Button>
        </div>

        <ErrorTestResults results={results} />

        <Alert message={
            '📊 After running tests, check your RUM dashboard under "Error Tracking" to see if the errors were captured. Look for errors with the source "browser" and check the error details and stack traces.'
        } />
      </CardContent>
    </Card>
  );
};
