import { NextResponse } from 'next/server';
import { resolveBackendOrigin } from '@/config/backendOrigin';
import { buildVersionedPath } from '@/server/backendRoutes';

const BACKEND_URL = resolveBackendOrigin();

const INTERNAL_PROXY_API_KEY = (
  process.env['INTERNAL_PROXY_API_KEY'] ||
  process.env['BACKEND_API_KEY'] ||
  process.env['INTERNAL_API_SECRET'] ||
  ''
).trim();

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

export async function GET(req: Request) {
  const url = new URL(req.url);
  const query = url.searchParams.toString();
  const headers: Record<string, string> = {};

  const authorization = req.headers.get('authorization');
  if (authorization) {
    headers['Authorization'] = authorization;
  }

  if (INTERNAL_PROXY_API_KEY) {
    headers['X-Internal-API-Key'] = INTERNAL_PROXY_API_KEY;
  }

  const backendUrl = `${BACKEND_URL}${buildVersionedPath('debug', 'model-usage')}${query ? `?${query}` : ''}`;

  try {
    const response = await fetchWithTimeout(
      backendUrl,
      {
        method: 'GET',
        headers,
      },
      10000
    );

    const body = (await safeJson(response)) ?? {
      detail: 'Backend returned a non-JSON response',
    };

    const nextHeaders = new Headers();
    const correlationId = response.headers.get('x-correlation-id');
    if (correlationId) {
      nextHeaders.set('X-Correlation-ID', correlationId);
    }

    return NextResponse.json(body, {
      status: response.status,
      headers: nextHeaders,
    });
  } catch {
    return NextResponse.json({ detail: 'Backend unreachable' }, { status: 502 });
  }
}
