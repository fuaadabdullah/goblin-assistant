import { NextResponse } from 'next/server';
import { resolveBackendOrigin } from '@/config/backendOrigin';

const BACKEND_URL = resolveBackendOrigin();

const INTERNAL_PROXY_API_KEY = (
  process.env.INTERNAL_PROXY_API_KEY ||
  process.env.BACKEND_API_KEY ||
  process.env.INTERNAL_API_SECRET ||
  ''
).trim();

interface ForwardResponse {
  status: number;
  body: unknown;
  correlationId?: string;
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

async function forwardValidate(req: Request): Promise<ForwardResponse> {
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    const authorization = req.headers.get('authorization');
    if (authorization) {
      headers.Authorization = authorization;
    }

    if (INTERNAL_PROXY_API_KEY) {
      headers['X-Internal-API-Key'] = INTERNAL_PROXY_API_KEY;
    }

    const incoming = (await safeJson(req)) ?? {};

    const response = await fetchWithTimeout(
      `${BACKEND_URL}/api/v1/auth/validate`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify(incoming),
      },
      8000
    );

    const body = (await safeJson(response)) ?? {
      detail: 'Backend returned a non-JSON response',
    };

    return {
      status: response.status,
      body,
      correlationId: response.headers.get('x-correlation-id') || undefined,
    };
  } catch {
    return {
      status: 502,
      body: { error: 'Backend unreachable' },
    };
  }
}

export async function POST(req: Request) {
  const result = await forwardValidate(req);
  const headers = new Headers();
  if (result.correlationId) {
    headers.set('X-Correlation-ID', result.correlationId);
  }
  return NextResponse.json(result.body ?? {}, { status: result.status, headers });
}
