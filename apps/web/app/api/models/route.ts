import { NextResponse } from 'next/server';
import { resolveBackendOrigin } from '@/config/backendOrigin';

const BACKEND_URL = resolveBackendOrigin();

const INTERNAL_PROXY_API_KEY = (
  process.env['INTERNAL_PROXY_API_KEY'] ||
  process.env['BACKEND_API_KEY'] ||
  process.env['INTERNAL_API_SECRET'] ||
  ''
).trim();

interface ForwardModelsResult {
  status: number;
  body: unknown;
  correlationId?: string | undefined;
  transportError?: boolean | undefined;
  fallbackUsed?: boolean | undefined;
}

async function safeJson<T = unknown>(res: Response): Promise<T | null> {
  try {
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number
): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }
}

function logProxyEvent(payload: {
  proxy_mode: 'thin';
  backend_status: number | null;
  legacy_fallback_used: boolean;
  correlation_id?: string | undefined;
  latency_ms: number;
}) {
  console.warn('[api/models] proxy_event', payload);
}

function buildEmptyRegistryFallback(reason: string): Record<string, unknown> {
  return {
    models: [],
    providers: [],
    router_models: [],
    source: 'frontend_registry_fallback',
    total_models: 0,
    total_providers: 0,
    total_router_models: 0,
    fallback_reason: reason,
  };
}

async function forwardToBackendModels(): Promise<ForwardModelsResult> {
  const buildHeaders = (): Record<string, string> => {
    const headers: Record<string, string> = {};
    if (INTERNAL_PROXY_API_KEY) {
      headers['X-Internal-API-Key'] = INTERNAL_PROXY_API_KEY;
    }
    return headers;
  };

  const requestBackend = async (path: string): Promise<ForwardModelsResult> => {
    const response = await fetchWithTimeout(
      `${BACKEND_URL}${path}`,
      {
        method: 'GET',
        headers: buildHeaders(),
      },
      10000
    );

    const body = (await safeJson(response)) ?? {
      detail: 'Backend returned a non-JSON response',
    };

    return {
      status: response.status,
      body,
      correlationId: response.headers.get('x-correlation-id') || undefined,
    };
  };

  const mapRoutingProvidersFallback = (raw: unknown): Record<string, unknown> => {
    const providerNames = Array.isArray(raw)
      ? raw.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
      : [];

    return {
      models: [],
      providers: providerNames.map((id) => ({
        id,
        health: 'unknown',
        configured: true,
        is_selectable: true,
        health_reason: null,
      })),
      source: 'routing_providers_fallback',
      total_models: 0,
      total_providers: providerNames.length,
    };
  };

  try {
    const primary = await requestBackend('/api/v1/providers/models');
    if (primary.status >= 200 && primary.status < 300) {
      return primary;
    }

    if (primary.status === 404) {
      const routingProviders = await requestBackend('/api/v1/routing/providers');
      if (routingProviders.status >= 200 && routingProviders.status < 300) {
        return {
          status: 200,
          body: mapRoutingProvidersFallback(routingProviders.body),
          correlationId: routingProviders.correlationId,
          fallbackUsed: true,
        };
      }
    }

    if ([401, 403, 404, 500, 502, 503].includes(primary.status)) {
      return {
        status: 200,
        body: buildEmptyRegistryFallback(`backend_status_${primary.status}`),
        correlationId: primary.correlationId,
        fallbackUsed: true,
      };
    }

    return {
      ...primary,
      fallbackUsed: false,
    };
  } catch {
    return {
      status: 200,
      body: buildEmptyRegistryFallback('backend_unreachable'),
      transportError: true,
      fallbackUsed: true,
    };
  }
}

export async function GET() {
  const startedAt = Date.now();
  const result = await forwardToBackendModels();

  const headers = new Headers();
  if (result.correlationId) {
    headers.set('X-Correlation-ID', result.correlationId);
  }

  logProxyEvent({
    proxy_mode: 'thin',
    backend_status: result.transportError ? null : result.status,
    legacy_fallback_used: Boolean(result.fallbackUsed),
    correlation_id: result.correlationId,
    latency_ms: Date.now() - startedAt,
  });

  return NextResponse.json(result.body ?? {}, { status: result.status, headers });
}
