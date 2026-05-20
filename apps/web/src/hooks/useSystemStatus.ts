import { useEffect, useRef, useState, useCallback } from 'react';
import { devError } from '@/utils/dev-log';

type ServiceState = 'ok' | 'degraded' | 'down' | 'unknown';

export type SystemStatus = {
  models: ServiceState;
  routing: ServiceState;
  sandbox: ServiceState;
  updatedAt?: string;
};

const DEFAULT: SystemStatus = {
  models: 'unknown',
  routing: 'unknown',
  sandbox: 'unknown',
};

interface ModelHealth {
  health?: string;
  health_reason?: string;
}

type StatusOptions = Readonly<{
  pollIntervalMs?: number;
  useWebSocket?: boolean;
  endpoints?: Readonly<{
    models?: string;
    routing?: string;
    sandbox?: string;
  }>;
}>;

/**
 * Aggregates system health from backend endpoints or demo API.
 * Supports polling (default) or websocket for real-time updates.
 * Falls back gracefully if endpoints are unavailable.
 *
 * @example
 * // Use real backend endpoints
 * const { status, refresh } = useSystemStatus({
 *   endpoints: { models: '/api/models', routing: '/api/routing' }
 * });
 *
 * @example
 * // Enable websocket for real-time updates
 * const { status } = useSystemStatus({ useWebSocket: true });
 */
export function useSystemStatus(opts?: StatusOptions) {
  const {
    pollIntervalMs = 15000,
    useWebSocket = false,
    endpoints = {},
  } = opts ?? {};

  const [status, setStatus] = useState<SystemStatus>(DEFAULT);
  const [loading, setLoading] = useState(true);
  const mounted = useRef(true);
  const wsRef = useRef<WebSocket | null>(null);

  // Map model health state to ServiceState
  const mapHealth = (h: string | undefined): ServiceState => {
    if (!h) return 'unknown';
    const lower = h.toLowerCase();
    if (lower.includes('unhealthy') || lower.includes('error') || lower.includes('down'))
      return 'down';
    if (lower.includes('degraded') || lower.includes('warning')) return 'degraded';
    if (lower.includes('healthy') || lower.includes('ok') || lower.includes('running'))
      return 'ok';
    return 'unknown';
  };

  const extractServiceHealth = useCallback(
    async (response: PromiseSettledResult<Response | null>, field: string): Promise<ServiceState> => {
      if (response.status === 'fulfilled' && response.value?.ok) {
        try {
          const data = (await response.value.json()) as Record<string, unknown>;
          if (field === 'models' && Array.isArray(data.models)) {
            const firstModel = data.models[0] as ModelHealth | undefined;
            return mapHealth(firstModel?.health);
          }
          if (field === 'routing' || field === 'sandbox') {
            return mapHealth(data.status as string | undefined);
          }
        } catch {
          // Continue on parse error
        }
      }
      return 'unknown';
    },
    [],
  );

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    try {
      const [modelsRes, routingRes, sandboxRes] = await Promise.allSettled([
        endpoints.models ? fetch(endpoints.models) : Promise.resolve(null),
        endpoints.routing ? fetch(endpoints.routing) : Promise.resolve(null),
        endpoints.sandbox ? fetch(endpoints.sandbox) : Promise.resolve(null),
      ]);

      const models = await extractServiceHealth(modelsRes, 'models');
      const routing = await extractServiceHealth(routingRes, 'routing');
      const sandbox = await extractServiceHealth(sandboxRes, 'sandbox');

      // If all default and demo API available, use fallback
      if (models === 'unknown' && routing === 'unknown' && sandbox === 'unknown') {
        const res = await fetch('/api/system-status');
        if (res.ok) {
          const data = (await res.json()) as SystemStatus;
          if (mounted.current) setStatus(data || DEFAULT);
          setLoading(false);
          return;
        }
      }

      if (mounted.current) {
        setStatus({ models, routing, sandbox, updatedAt: new Date().toISOString() });
      }
    } catch (e) {
      devError('[useSystemStatus] fetch error', e);
      if (mounted.current) setStatus(DEFAULT);
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, [endpoints, extractServiceHealth]);

  const connectWebSocket = useCallback(() => {
    if (!useWebSocket) return;
    try {
      // Example: connect to wss://your-backend/health-stream
      // Configure your real websocket endpoint here
      const proto =
        globalThis.location?.protocol === 'https:' ? 'wss:' : 'ws:';
      const hostPart = endpoints.models?.split('://')[1]?.split('/')[0] ?? 'localhost:3000';
      const wsUrl = `${proto}//${hostPart}/health-stream`;
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as SystemStatus;
          if (mounted.current) setStatus(data);
        } catch {
          // Silently ignore malformed messages
        }
      };

      wsRef.current.onerror = () => {
        // Fallback to polling on ws error
        if (mounted.current) fetchStatus();
      };
    } catch {
      // Fallback to polling if ws not supported
      fetchStatus();
    }
  }, [useWebSocket, endpoints, fetchStatus]);

  useEffect(() => {
    mounted.current = true;
    if (useWebSocket) {
      connectWebSocket();
    } else {
      fetchStatus();
      const id = setInterval(fetchStatus, pollIntervalMs);
      return () => clearInterval(id);
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      mounted.current = false;
    };
  }, [fetchStatus, pollIntervalMs, useWebSocket, connectWebSocket]);

  return { status, loading, refresh: fetchStatus } as const;
}
