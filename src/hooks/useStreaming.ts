// hooks/useStreaming.ts
'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { apiClient } from '../../lib/services';

export function useStreaming() {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const abortControllerRef = useRef<any>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();

  // Connect to streaming endpoint
  const connect = useCallback(async (
    endpoint: string,
    onChunk: (chunk: unknown) => void,
    onError?: (error: Error) => void,
    onComplete?: () => void
  ) => {
    // Cancel existing connection
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    abortControllerRef.current = new (globalThis as any).AbortController();

    try {
      setError(null);
      setIsConnected(true);

      const stream = apiClient.stream(endpoint);

      for await (const chunk of stream) {
        // Check if aborted
        if (abortControllerRef.current?.signal.aborted) {
          break;
        }

        onChunk(chunk);
      }

      if (onComplete) {
        onComplete();
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Streaming failed';
      setError(errorMessage);

      if (onError) {
        onError(err instanceof Error ? err : new Error(errorMessage));
      }
    } finally {
      setIsConnected(false);
      abortControllerRef.current = null;
    }
  }, []);

  // Connect via WebSocket
  const connectWebSocket = useCallback((
    endpoint: string,
    onMessage: (data: unknown) => void,
    onError?: (error: Event) => void,
    onOpen?: () => void,
    onClose?: () => void
  ) => {
    try {
      setError(null);
      const ws = apiClient.connectWebSocket(endpoint);

      ws.onopen = () => {
        setIsConnected(true);
        if (onOpen) onOpen();
      };

      ws.onmessage = (event: unknown) => {
        try {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const data = JSON.parse((event as any).data);
          onMessage(data);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (event: unknown) => {
        setError('WebSocket connection failed');
        if (onError) onError(event as Event);
      };

      ws.onclose = () => {
        setIsConnected(false);
        if (onClose) onClose();
      };

      return ws;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'WebSocket connection failed';
      setError(errorMessage);
      if (onError) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        onError(err as any);
      }
      return null;
    }
  }, []);

  // Disconnect
  const disconnect = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsConnected(false);
    setError(null);
  }, []);

  // Auto-reconnect functionality
  const connectWithRetry = useCallback(async (
    endpoint: string,
    onChunk: (chunk: unknown) => void,
    maxRetries = 3,
    retryDelay = 1000
  ) => {
    let retries = 0;

    const attemptConnect = async () => {
      try {
        await connect(endpoint, onChunk);
      } catch (err) {
        retries++;
        if (retries < maxRetries) {
          reconnectTimeoutRef.current = setTimeout(attemptConnect, retryDelay * retries);
        } else {
          setError('Max retries exceeded');
        }
      }
    };

    await attemptConnect();
  }, [connect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [disconnect]);

  return {
    connect,
    connectWebSocket,
    connectWithRetry,
    disconnect,
    isConnected,
    error,
  };
}
