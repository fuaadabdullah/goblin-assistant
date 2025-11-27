// src/hooks/useProviderRouter.ts
import { useState, useCallback } from 'react';
import router from '../routing/router'; // the TS router you already have

type ChunkHandler = (chunk: any) => void;
type MetaHandler = (meta: any) => void;
type ErrorHandler = (error: any) => void;

interface StreamOptions {
  onChunk: ChunkHandler;
  onMeta?: MetaHandler;
  onDone?: () => void;
  onError?: ErrorHandler;
  fallbackToPolling?: boolean;
  pollingInterval?: number;
  maxRetries?: number;
}

export function useProviderRouter() {
  const [metricsAvailable, _setMetricsAvailable] = useState(false);
  const [connectionHealth, setConnectionHealth] = useState<
    'unknown' | 'healthy' | 'degraded' | 'failed'
  >('unknown');

  function topProviders(capability: string, preferLocal = false, preferCost = false, limit = 6) {
    return router.topProvidersFor(capability, preferLocal, preferCost, limit);
  }

  async function routeTask(
    taskType: string,
    payload: any,
    opts?: { preferLocal?: boolean; preferCost?: boolean }
  ) {
    const res = await fetch('/api/route_task', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_type: taskType, payload, opts }),
    });
    return await res.json();
  }

  // Health check for streaming connections
  const checkStreamingHealth = useCallback(async (): Promise<boolean> => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5s timeout

      const resp = await fetch('/api/health/stream', {
        method: 'GET',
        signal: controller.signal,
        headers: { 'Cache-Control': 'no-cache' },
      });

      clearTimeout(timeoutId);
      const isHealthy = resp.ok;
      setConnectionHealth(isHealthy ? 'healthy' : 'degraded');
      return isHealthy;
    } catch (error) {
      setConnectionHealth('failed');
      return false;
    }
  }, []);

  // Polling fallback for streaming
  async function routeTaskStreamPolling(
    taskType: string,
    payload: any,
    options: StreamOptions,
    opts?: { preferLocal?: boolean; preferCost?: boolean }
  ) {
    const { onChunk, onMeta, onDone, onError, pollingInterval = 1000, maxRetries = 30 } = options;

    try {
      // Start the stream
      const startResp = await fetch('/api/route_task_stream_start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_type: taskType, payload, opts }),
      });

      if (!startResp.ok) {
        throw new Error(`Stream start failed: ${startResp.status}`);
      }

      const { stream_id } = await startResp.json();
      onMeta?.({ provider: 'unknown', model: 'unknown', stream_id, fallback: 'polling' });

      let retryCount = 0;
      const poll = async () => {
        try {
          const pollResp = await fetch(`/api/route_task_stream_poll/${stream_id}`);
          if (!pollResp.ok) {
            if (pollResp.status === 404) {
              // Stream completed
              onDone?.();
              return;
            }
            throw new Error(`Poll failed: ${pollResp.status}`);
          }

          const data = await pollResp.json();
          if (data.chunks) {
            data.chunks.forEach((chunk: any) => onChunk?.(chunk));
          }

          if (data.done) {
            onDone?.();
            return;
          }

          // Continue polling
          setTimeout(poll, pollingInterval);
        } catch (error) {
          retryCount++;
          if (retryCount < maxRetries) {
            setTimeout(poll, pollingInterval);
          } else {
            onError?.(error);
            onDone?.();
          }
        }
      };

      // Start polling
      setTimeout(poll, pollingInterval);

      // Return cleanup function
      return () => {
        fetch(`/api/route_task_stream_cancel/${stream_id}`, { method: 'POST' }).catch(() => {});
      };
    } catch (error) {
      onError?.(error);
      onDone?.();
      return () => {};
    }
  }

  function routeTaskStream(
    taskType: string,
    payload: any,
    options: StreamOptions,
    opts?: { preferLocal?: boolean; preferCost?: boolean }
  ) {
    const { onChunk, onMeta, onDone, onError, fallbackToPolling = true } = options;
    const controller = new AbortController();

    // Check if we're in SSR environment
    const isSSR = typeof window === 'undefined';

    // For SSR, always use polling fallback
    if (isSSR) {
      return routeTaskStreamPolling(taskType, payload, options, opts);
    }

    // Try SSE first, fallback to polling if it fails
    const trySSE = async () => {
      try {
        const esUrl = '/api/route_task_stream';
        const resp = await fetch(esUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ task_type: taskType, payload, opts }),
          signal: controller.signal,
        });

        if (!resp.ok) {
          throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
        }

        // Check if response is actually SSE (not buffered)
        const contentType = resp.headers.get('content-type');
        if (!contentType?.includes('text/event-stream')) {
          throw new Error('Response is not SSE, likely buffered by proxy');
        }

        const reader = resp.body?.getReader();
        if (!reader) {
          throw new Error('No response body reader available');
        }

        const decoder = new TextDecoder();
        let buffer = '';
        let sseWorking = false;
        let timeoutId: NodeJS.Timeout;

        // Set a timeout to detect if SSE is being buffered
        const sseTimeout = new Promise<never>((_, reject) => {
          timeoutId = setTimeout(() => reject(new Error('SSE timeout - likely buffered')), 3000);
        });

        const processStream = async () => {
          try {
            // eslint-disable-next-line no-constant-condition
            while (true) {
              const readPromise = reader.read();
              const result = await Promise.race([readPromise, sseTimeout]);

              if (result.done) break;

              clearTimeout(timeoutId);
              sseWorking = true; // If we get here, SSE is working

              buffer += decoder.decode(result.value, { stream: true });

              // split by SSE event separator
              const parts = buffer.split('\n\n');
              buffer = parts.pop() || '';

              for (const part of parts) {
                const lines = part.split('\n');
                let event = 'message';
                let data = '';
                for (const line of lines) {
                  if (line.startsWith('event:')) event = line.replace('event:', '').trim();
                  else if (line.startsWith('data:')) data += line.replace('data:', '').trim();
                }

                if (event === 'meta') {
                  try {
                    onMeta?.(JSON.parse(data));
                  } catch {
                    onMeta?.(data);
                  }
                } else if (event === 'done') {
                  onDone?.();
                  return;
                } else {
                  try {
                    onChunk?.(JSON.parse(data));
                  } catch {
                    onChunk?.(data);
                  }
                }
              }
            }
            onDone?.();
          } catch (error) {
            if (!sseWorking && fallbackToPolling) {
              console.warn('SSE failed, falling back to polling:', error);
              // Fallback to polling
              return routeTaskStreamPolling(taskType, payload, options, opts);
            } else {
              onError?.(error);
              onDone?.();
            }
          }
        };

        processStream();
      } catch (error) {
        if (fallbackToPolling) {
          console.warn('SSE failed, falling back to polling:', error);
          // Fallback to polling
          return routeTaskStreamPolling(taskType, payload, options, opts);
        } else {
          onError?.(error);
          onDone?.();
        }
      }
    };

    trySSE();

    return () => controller.abort();
  }

  return {
    topProviders,
    routeTask,
    routeTaskStream,
    checkStreamingHealth,
    connectionHealth,
    metricsAvailable,
  };
}
