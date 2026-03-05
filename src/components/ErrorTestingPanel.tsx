'use client';

import React, { useState } from 'react';
import { Button } from './ui/Button';
import { Alert } from './ui/Alert';

export const ErrorTestingPanel: React.FC = () => {
  const [errorType, setErrorType] = useState<'network' | 'validation' | 'server' | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const triggerError = async (type: 'network' | 'validation' | 'server') => {
    setErrorType(type);
    setIsLoading(true);
    setErrorMessage(null);

    try {
      let endpoint = '';
      let method = 'GET';
      let body = null;

      switch (type) {
        case 'network':
          endpoint = '/api/nonexistent-endpoint';
          break;
        case 'validation':
          endpoint = '/api/auth/login';
          method = 'POST';
          body = JSON.stringify({ email: 'invalid-email', password: '' });
          break;
        case 'server':
          endpoint = '/api/chat/stream';
          method = 'POST';
          body = JSON.stringify({ message: 'This should cause a server error' });
          break;
      }

      const response = await fetch(endpoint, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Success response:', data);
    } catch (error) {
      console.error('Error triggered:', error);
      setErrorMessage(error instanceof Error ? error.message : 'Unknown error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-gray-900">Error Testing Panel</h2>

      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Button
            onClick={() => triggerError('network')}
            disabled={isLoading}
            variant="outline"
            className="justify-start"
          >
            {isLoading && errorType === 'network' ? 'Testing...' : 'Test 404 Error'}
          </Button>

          <Button
            onClick={() => triggerError('validation')}
            disabled={isLoading}
            variant="outline"
            className="justify-start"
          >
            {isLoading && errorType === 'validation' ? 'Testing...' : 'Test Validation Error'}
          </Button>

          <Button
            onClick={() => triggerError('server')}
            disabled={isLoading}
            variant="outline"
            className="justify-start"
          >
            {isLoading && errorType === 'server' ? 'Testing...' : 'Test Server Error'}
          </Button>
        </div>
      </div>

      {errorMessage && (
        <Alert variant="destructive">
          <div className="font-medium">Error Triggered</div>
          <div className="text-sm mt-1">{errorMessage}</div>
        </Alert>
      )}

      <div className="bg-gray-50 p-4 rounded-lg">
        <h3 className="font-medium text-gray-900 mb-2">Instructions</h3>
        <ul className="space-y-2 text-sm text-gray-600">
          <li>• 404 Error: Tests non-existent endpoint handling</li>
          <li>• Validation Error: Tests input validation failures</li>
          <li>• Server Error: Tests server-side error handling</li>
          <li>• Check console for detailed error logs</li>
        </ul>
      </div>
    </div>
  );
};
