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

type TimedFetchResponse = {
  response: Response;
  clearTimeout: () => void;
};

async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number
): Promise<TimedFetchResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  let cleared = false;
  const clearTimeoutOnce = () => {
    if (cleared) {
      return;
    }
    cleared = true;
    clearTimeout(timeout);
  };

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return { response, clearTimeout: clearTimeoutOnce };
  } catch (error) {
    clearTimeoutOnce();
    throw error;
  }
}

function streamBodyWithCleanup(
  body: ReadableStream<Uint8Array> | null,
  clearTimeout: () => void
): ReadableStream<Uint8Array> | null {
  if (!body) {
    clearTimeout();
    return null;
  }

  const reader = body.getReader();
  return new ReadableStream<Uint8Array>({
    async pull(controller) {
      try {
        const { done, value } = await reader.read();
        if (done) {
          clearTimeout();
          controller.close();
          return;
        }
        controller.enqueue(value);
      } catch (error) {
        clearTimeout();
        controller.error(error);
      }
    },
    async cancel(reason) {
      clearTimeout();
      await reader.cancel(reason);
    },
  });
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
    const { response, clearTimeout } = await fetchWithTimeout(
      backendUrl,
      await buildRequestInit(req),
      10000
    );
    const nextHeaders = new Headers();

    const correlationId = response.headers.get('x-correlation-id');
    if (correlationId) {
      nextHeaders.set('X-Correlation-ID', correlationId);
    }

    const contentType = response.headers.get('content-type') || '';
    if (contentType.toLowerCase().includes('application/json')) {
      try {
        const payload = (await safeJson(response)) ?? {
          detail: 'Backend returned a non-JSON response',
        };
        return NextResponse.json(payload, {
          status: response.status,
          headers: nextHeaders,
        });
      } finally {
        clearTimeout();
      }
    }

    if (contentType) {
      nextHeaders.set('Content-Type', contentType);
    }

    const body = streamBodyWithCleanup(response.body, clearTimeout);
    try {
      return new NextResponse(body, {
        status: response.status,
        headers: nextHeaders,
      });
    } catch (error) {
      clearTimeout();
      throw error;
    }
  } catch {
    return NextResponse.json({ detail: 'Backend unreachable' }, { status: 502 });
  }
}
