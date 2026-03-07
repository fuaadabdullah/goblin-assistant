import type { NextApiRequest, NextApiResponse } from 'next';
import { resolveBackendOrigin } from '../../config/backendOrigin';

const BACKEND_URL = resolveBackendOrigin();

const INTERNAL_PROXY_API_KEY =
  (process.env.INTERNAL_PROXY_API_KEY ||
    process.env.BACKEND_API_KEY ||
    process.env.INTERNAL_API_SECRET ||
    '').trim();

interface ForwardModelsResult {
  status: number;
  body: unknown;
  correlationId?: string;
  transportError?: boolean;
  fallbackUsed?: boolean;
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
  timeoutMs: number,
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
  correlation_id?: string;
  latency_ms: number;
}) {
  console.info('[api/models] proxy_event', payload);
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
      10000,
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

  const mapOpsStatusFallback = (raw: unknown): Record<string, unknown> => {
    const providersRaw =
      raw && typeof raw === 'object' && !Array.isArray(raw)
        ? (raw as { providers?: unknown }).providers
        : undefined;

    const providersRecord =
      providersRaw && typeof providersRaw === 'object' && !Array.isArray(providersRaw)
        ? (providersRaw as Record<string, unknown>)
        : {};

    const providers: Array<Record<string, unknown>> = [];
    const models: Array<Record<string, unknown>> = [];

    for (const [providerId, entry] of Object.entries(providersRecord)) {
      if (!providerId.trim()) continue;
      const detail =
        entry && typeof entry === 'object' && !Array.isArray(entry)
          ? (entry as Record<string, unknown>)
          : {};

      const health =
        typeof detail.status === 'string' && detail.status.trim()
          ? detail.status.trim().toLowerCase()
          : 'unknown';

      const healthReason =
        typeof detail.error === 'string' && detail.error.trim()
          ? detail.error.trim()
          : null;

      const isSelectable = health !== 'unhealthy';

      providers.push({
        id: providerId,
        health,
        configured: true,
        is_selectable: isSelectable,
        health_reason: healthReason,
      });

      const modelList = Array.isArray(detail.models) ? detail.models : [];
      for (const model of modelList) {
        if (typeof model !== 'string' || !model.trim()) continue;
        models.push({
          name: model,
          provider: providerId,
          health,
          is_selectable: isSelectable,
          health_reason: healthReason,
        });
      }
    }

    return {
      models,
      providers,
      source: 'ops_provider_status_fallback',
      total_models: models.length,
      total_providers: providers.length,
    };
  };

  const mapRoutingProvidersFallback = (raw: unknown): Record<string, unknown> => {
    const providerNames = Array.isArray(raw)
      ? raw.filter(
          (item): item is string => typeof item === 'string' && item.trim().length > 0,
        )
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
    const primary = await requestBackend('/providers/models');
    if (primary.status !== 404) {
      return primary;
    }

    const opsStatus = await requestBackend('/ops/providers/status');
    if (opsStatus.status >= 200 && opsStatus.status < 300) {
      return {
        status: 200,
        body: mapOpsStatusFallback(opsStatus.body),
        correlationId: opsStatus.correlationId,
        fallbackUsed: true,
      };
    }

    if (opsStatus.status !== 404) {
      return {
        ...opsStatus,
        fallbackUsed: true,
      };
    }

    const routingProviders = await requestBackend('/routing/providers');
    if (routingProviders.status >= 200 && routingProviders.status < 300) {
      return {
        status: 200,
        body: mapRoutingProvidersFallback(routingProviders.body),
        correlationId: routingProviders.correlationId,
        fallbackUsed: true,
      };
    }

    return {
      ...primary,
      fallbackUsed: false,
    };
  } catch {
    return {
      status: 502,
      body: { error: 'Backend unreachable' },
      transportError: true,
    };
  }
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const startedAt = Date.now();
  const result = await forwardToBackendModels();

  if (result.correlationId) {
    res.setHeader('X-Correlation-ID', result.correlationId);
  }

  res.status(result.status).json(result.body ?? {});

  logProxyEvent({
    proxy_mode: 'thin',
    backend_status: result.transportError ? null : result.status,
    legacy_fallback_used: Boolean(result.fallbackUsed),
    correlation_id: result.correlationId,
    latency_ms: Date.now() - startedAt,
  });
}
