import type { NextApiRequest, NextApiResponse } from 'next';
import { resolveBackendOrigin } from '../../config/backendOrigin';

const BACKEND_URL = resolveBackendOrigin();

const INTERNAL_PROXY_API_KEY =
  (process.env.INTERNAL_PROXY_API_KEY ||
    process.env.BACKEND_API_KEY ||
    process.env.INTERNAL_API_SECRET ||
    '').trim();

interface ForwardResponse {
  status: number;
  body: unknown;
  correlationId?: string;
  requestId?: string;
  licenseTier?: string;
  transportError?: boolean;
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

function getRequestHeader(req: NextApiRequest, name: string): string | undefined {
  const value = req.headers[name.toLowerCase()];
  if (Array.isArray(value)) return value.join(', ');
  if (typeof value === 'string' && value.trim()) return value.trim();
  return undefined;
}

function logProxyEvent(payload: {
  proxy_mode: 'thin';
  backend_status: number | null;
  legacy_fallback_used: boolean;
  correlation_id?: string;
  latency_ms: number;
}) {
  console.info('[api/generate] proxy_event', payload);
}

function writeResponse(
  res: NextApiResponse,
  result: {
    status: number;
    body: unknown;
    correlationId?: string;
    requestId?: string;
    licenseTier?: string;
  },
) {
  if (result.correlationId) res.setHeader('X-Correlation-ID', result.correlationId);
  if (result.requestId) res.setHeader('X-Request-ID', result.requestId);
  if (result.licenseTier) res.setHeader('X-License-Tier', result.licenseTier);
  return res.status(result.status).json(result.body ?? {});
}

/**
 * Build the request body for the backend /api/chat endpoint.
 * The frontend may send {prompt, messages, model, provider} but the
 * backend expects {messages: [{role, content}], model?, provider?}.
 */
function buildChatRequestBody(incoming: Record<string, unknown>): Record<string, unknown> {
  let messages = incoming.messages as Array<Record<string, unknown>> | undefined;

  // If no messages provided, convert prompt into a single user message.
  if ((!messages || !Array.isArray(messages) || messages.length === 0) && incoming.prompt) {
    messages = [{ role: 'user', content: String(incoming.prompt) }];
  }

  // Strip extra fields from each message — backend only accepts role & content.
  const cleanMessages = (messages ?? []).map((m) => ({
    role: String(m.role ?? 'user'),
    content: String(m.content ?? ''),
  }));

  return {
    messages: cleanMessages,
    ...(incoming.model ? { model: incoming.model } : {}),
    ...(incoming.provider ? { provider: incoming.provider } : {}),
  };
}

/**
 * Map the backend SimpleChatResponse {ok, result: {text}, provider, model}
 * to the frontend ChatResponse {content, model, provider}.
 */
function mapBackendResponse(body: Record<string, unknown>): Record<string, unknown> {
  if (body.ok === true && body.result && typeof body.result === 'object') {
    const result = body.result as Record<string, unknown>;
    return {
      content: result.text ?? '',
      model: body.model ?? undefined,
      provider: body.provider ?? undefined,
    };
  }
  // Error case — pass through for the frontend error parser.
  return {
    error: body.error ?? 'Unknown backend error',
    detail: body.error ?? 'Unknown backend error',
  };
}

async function forwardToBackendGenerate(
  req: NextApiRequest,
): Promise<ForwardResponse> {
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (INTERNAL_PROXY_API_KEY) {
      headers['X-Internal-API-Key'] = INTERNAL_PROXY_API_KEY;
    }

    const forwardedFor = getRequestHeader(req, 'x-forwarded-for');
    if (forwardedFor) {
      headers['X-Forwarded-For'] = forwardedFor;
    }

    const chatBody = buildChatRequestBody((req.body ?? {}) as Record<string, unknown>);

    const response = await fetchWithTimeout(
      `${BACKEND_URL}/api/chat`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify(chatBody),
      },
      30000,
    );

    const raw = (await safeJson<Record<string, unknown>>(response)) ?? {
      detail: 'Backend returned a non-JSON response',
    };

    // Map the backend response format to what the frontend expects.
    const body = response.ok ? mapBackendResponse(raw) : raw;

    return {
      status: response.status,
      body,
      correlationId: response.headers.get('x-correlation-id') || undefined,
      requestId: response.headers.get('x-request-id') || undefined,
      licenseTier: response.headers.get('x-license-tier') || undefined,
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
  if (req.method !== 'POST') {
    return res.status(405).json({ detail: 'Method not allowed' });
  }

  const startedAt = Date.now();
  const result = await forwardToBackendGenerate(req);

  writeResponse(res, {
    status: result.status,
    body: result.body,
    correlationId: result.correlationId,
    requestId: result.requestId,
    licenseTier: result.licenseTier,
  });

  logProxyEvent({
    proxy_mode: 'thin',
    backend_status: result.transportError ? null : result.status,
    legacy_fallback_used: false,
    correlation_id: result.correlationId,
    latency_ms: Date.now() - startedAt,
  });
}
