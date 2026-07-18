import { NextResponse } from 'next/server';
import { resolveBackendOrigin } from '@/config/backendOrigin';

const BACKEND_URL = resolveBackendOrigin();

const INTERNAL_PROXY_API_KEY = (
  process.env['INTERNAL_PROXY_API_KEY'] ||
  process.env['BACKEND_API_KEY'] ||
  process.env['INTERNAL_API_SECRET'] ||
  ''
).trim();

async function safeJson<T = unknown>(response: Response): Promise<T | null> {
  try {
    return (await response.json()) as T;
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

function buildHeaders(req: Request): Record<string, string> {
  const headers: Record<string, string> = {};

  const authorization = req.headers.get('authorization');
  if (authorization) {
    headers['Authorization'] = authorization;
  }

  const contentType = req.headers.get('content-type');
  if (contentType) {
    headers['Content-Type'] = contentType;
  }

  const correlationId = req.headers.get('x-correlation-id');
  if (correlationId) {
    headers['X-Correlation-ID'] = correlationId;
  }

  if (INTERNAL_PROXY_API_KEY) {
    headers['X-Internal-API-Key'] = INTERNAL_PROXY_API_KEY;
  }

  return headers;
}

async function buildRequestInit(req: Request): Promise<RequestInit> {
  const requestInit: RequestInit = {
    method: req.method,
    headers: buildHeaders(req),
  };

  if (req.method !== 'GET' && req.method !== 'HEAD') {
    const body = await req.arrayBuffer();
    if (body.byteLength > 0) {
      requestInit.body = Buffer.from(body);
    }
  }

  return requestInit;
}

function buildBackendUrl(req: Request, backendBasePath: string, suffixPath = ''): string {
  const url = new URL(req.url);
  const query = url.searchParams.toString();
  const suffix = suffixPath.trim() ? `/${suffixPath.replace(/^\/+/, '')}` : '';
  return `${BACKEND_URL}${backendBasePath}${suffix}${query ? `?${query}` : ''}`;
}

export async function forwardRequest(
  req: Request,
  backendBasePath: string,
  suffixPath = ''
): Promise<Response> {
  const backendUrl = buildBackendUrl(req, backendBasePath, suffixPath);

  try {
    const response = await fetchWithTimeout(backendUrl, await buildRequestInit(req), 10000);
    const nextHeaders = new Headers();

    const correlationId = response.headers.get('x-correlation-id');
    if (correlationId) {
      nextHeaders.set('X-Correlation-ID', correlationId);
    }

    const contentType = response.headers.get('content-type') || '';
    if (contentType.toLowerCase().includes('application/json')) {
      const payload = (await safeJson(response)) ?? {
        detail: 'Backend returned a non-JSON response',
      };
      return NextResponse.json(payload, {
        status: response.status,
        headers: nextHeaders,
      });
    }

    const payload = await response.text();
    if (contentType) {
      nextHeaders.set('Content-Type', contentType);
    }

    return new NextResponse(payload, {
      status: response.status,
      headers: nextHeaders,
    });
  } catch {
    return NextResponse.json({ detail: 'Backend unreachable' }, { status: 502 });
  }
}
