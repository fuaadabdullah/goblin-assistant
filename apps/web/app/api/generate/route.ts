import { NextResponse } from 'next/server';
import { resolveBackendOrigin } from '@/config/backendOrigin';

const BACKEND_URL = resolveBackendOrigin();

const INTERNAL_PROXY_API_KEY = (
  process.env['INTERNAL_PROXY_API_KEY'] ||
  process.env['BACKEND_API_KEY'] ||
  process.env['INTERNAL_API_SECRET'] ||
  ''
).trim();

interface ForwardResponse {
  status: number;
  body: unknown;
  correlationId?: string | undefined;
  requestId?: string | undefined;
  licenseTier?: string | undefined;
  transportError?: boolean | undefined;
}

async function safeJson<T = unknown>(res: Request | Response): Promise<T | null> {
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
  runtime_unavailable: boolean;
  correlation_id?: string | undefined;
  latency_ms: number;
}) {
  console.warn('[api/generate] proxy_event', payload);
}

/**
 * Build the request body for the backend /api/v1/api/chat endpoint.
 * The frontend may send {prompt, messages, model, provider} but the
 * backend expects {messages: [{role, content}], model?, provider?}.
 */
function buildChatRequestBody(incoming: Record<string, unknown>): Record<string, unknown> {
  let messages = incoming['messages'] as Array<Record<string, unknown>> | undefined;

  // If no messages provided, convert prompt into a single user message.
  if ((!messages || !Array.isArray(messages) || messages.length === 0) && incoming['prompt']) {
    messages = [{ role: 'user', content: String(incoming['prompt']) }];
  }

  // Strip extra fields from each message — backend only accepts role & content.
  const cleanMessages = (messages ?? []).map((m) => ({
    role: String(m['role'] ?? 'user'),
    content: String(m['content'] ?? ''),
  }));

  return {
    messages: cleanMessages,
    ...(incoming['model'] ? { model: incoming['model'] } : {}),
    ...(incoming['provider'] ? { provider: incoming['provider'] } : {}),
  };
}

/**
 * Map the backend SimpleChatResponse {ok, result: {text}, provider, model}
 * to the frontend ChatResponse {content, model, provider}.
 */
function mapBackendResponse(body: Record<string, unknown>): Record<string, unknown> {
  if (body['ok'] === true && body['result'] && typeof body['result'] === 'object') {
    const result = body['result'] as Record<string, unknown>;
    return {
      content: result['text'] ?? '',
      model: body['model'] ?? undefined,
      provider: body['provider'] ?? undefined,
    };
  }
  // Error case — pass through for the frontend error parser.
  return {
    error: body['error'] ?? 'Unknown backend error',
    detail: body['error'] ?? 'Unknown backend error',
  };
}

function buildRuntimeUnavailableBody(reason: string, detail?: unknown): Record<string, unknown> {
  return {
    error: 'real-runtime-unavailable',
    detail:
      typeof detail === 'string' && detail.trim()
        ? detail
        : 'Real model runtime is unavailable. Please try again later.',
    reason,
  };
}

function isMockProvider(value: unknown): boolean {
  return typeof value === 'string' && value.trim().toLowerCase() === 'mock';
}

function backendReturnedMock(body: Record<string, unknown>): boolean {
  return isMockProvider(body['provider']);
}

function backendUnavailableReason(body: Record<string, unknown>): string | null {
  const error = String(body['error'] ?? body['degraded_reason'] ?? body['detail'] ?? '');
  if (error === 'no-configured-providers') return 'no-configured-providers';
  if (error === 'provider-access-denied') return 'provider-access-denied';
  return null;
}

async function forwardToBackendGenerate(req: Request): Promise<ForwardResponse> {
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (INTERNAL_PROXY_API_KEY) {
      headers['X-Internal-API-Key'] = INTERNAL_PROXY_API_KEY;
    }

    const forwardedFor = req.headers.get('x-forwarded-for');
    if (forwardedFor) {
      headers['X-Forwarded-For'] = forwardedFor;
    }

    const incoming = ((await safeJson<Record<string, unknown>>(req)) ?? {}) as Record<
      string,
      unknown
    >;
    const chatBody = buildChatRequestBody(incoming);

    const response = await fetchWithTimeout(
      `${BACKEND_URL}/api/v1/api/chat`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify(chatBody),
      },
      30000
    );

    const raw = (await safeJson<Record<string, unknown>>(response)) ?? {
      detail: 'Backend returned a non-JSON response',
    };

    const unavailableReason = backendUnavailableReason(raw);
    const body = response.ok ? mapBackendResponse(raw) : raw;
    const mockRuntime = response.ok && (backendReturnedMock(raw) || backendReturnedMock(body));

    if (unavailableReason || mockRuntime) {
      return {
        status: 503,
        body: buildRuntimeUnavailableBody(
          unavailableReason ?? 'mock-provider-selected',
          raw['error'] ?? raw['detail']
        ),
        correlationId: response.headers.get('x-correlation-id') || undefined,
        requestId: response.headers.get('x-request-id') || undefined,
        licenseTier: response.headers.get('x-license-tier') || undefined,
      };
    }

    return {
      status: response.status,
      body,
      correlationId: response.headers.get('x-correlation-id') || undefined,
      requestId: response.headers.get('x-request-id') || undefined,
      licenseTier: response.headers.get('x-license-tier') || undefined,
    };
  } catch {
    return {
      status: 503,
      body: buildRuntimeUnavailableBody('backend-transport-error'),
      transportError: true,
    };
  }
}

export async function POST(req: Request) {
  const startedAt = Date.now();
  const result = await forwardToBackendGenerate(req);

  const headers = new Headers();
  if (result.correlationId) headers.set('X-Correlation-ID', result.correlationId);
  if (result.requestId) headers.set('X-Request-ID', result.requestId);
  if (result.licenseTier) headers.set('X-License-Tier', result.licenseTier);

  logProxyEvent({
    proxy_mode: 'thin',
    backend_status: result.transportError ? null : result.status,
    runtime_unavailable: result.status === 503,
    correlation_id: result.correlationId,
    latency_ms: Date.now() - startedAt,
  });

  return NextResponse.json(result.body ?? {}, { status: result.status, headers });
}
