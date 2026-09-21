import { NextResponse } from 'next/server';
import { resolveBackendOrigin } from '@/config/backendOrigin';

const BACKEND_URL = resolveBackendOrigin();

const INTERNAL_PROXY_API_KEY = (
  process.env['INTERNAL_PROXY_API_KEY'] ||
  process.env['BACKEND_API_KEY'] ||
  process.env['INTERNAL_API_SECRET'] ||
  ''
).trim();

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

  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout>;
  let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
  let downstream: ReadableStreamDefaultController<Uint8Array> | undefined;
  let finished = false;
  let idleTimeoutMs = 10000;

  const cleanup = () => {
    finished = true;
    clearTimeout(timer);
    req.signal.removeEventListener('abort', onAbort);
  };
  const abort = (reason: unknown) => {
    if (finished) return;
    cleanup();
    controller.abort(reason);
    downstream?.error(reason);
    void reader?.cancel(reason).catch(() => undefined);
  };
  const onAbort = () => abort(req.signal.reason);
  const armTimeout = () => {
    clearTimeout(timer);
    timer = setTimeout(() => abort(new Error('Backend response timed out')), idleTimeoutMs);
  };
  req.signal.addEventListener('abort', onAbort, { once: true });
  armTimeout();
  if (req.signal.aborted) onAbort();

  try {
    const response = await fetch(backendUrl, {
      ...(await buildRequestInit(req)),
      signal: controller.signal,
      cache: 'no-store',
    });
    const headers = new Headers();
    for (const name of ['content-type', 'x-correlation-id', 'cache-control', 'retry-after']) {
      const value = response.headers.get(name);
      if (value) headers.set(name, value);
    }
    if (!response.body || [204, 205, 304].includes(response.status)) {
      cleanup();
      return new NextResponse(null, { status: response.status, headers });
    }
    if (headers.get('content-type')?.includes('text/event-stream')) idleTimeoutMs = 30000;
    armTimeout();
    reader = response.body.getReader();
    const body = new ReadableStream<Uint8Array>({
      start(streamController) {
        downstream = streamController;
      },
      async pull(streamController) {
        try {
          const { done, value } = await reader!.read();
          if (finished) return;
          if (done) {
            cleanup();
            streamController.close();
          } else {
            armTimeout();
            streamController.enqueue(value);
          }
        } catch (error) {
          abort(error);
        }
      },
      async cancel(reason) {
        cleanup();
        controller.abort(reason);
        await reader!.cancel(reason);
      },
    });
    return new NextResponse(body, { status: response.status, headers });
  } catch {
    cleanup();
    controller.abort();
    return NextResponse.json({ detail: 'Backend unreachable' }, { status: 502 });
  }
}
