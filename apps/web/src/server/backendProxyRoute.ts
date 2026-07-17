import { NextResponse } from 'next/server';
import { resolveBackendOrigin } from '@/config/backendOrigin';
import { API_PROXY_ROUTES, type ApiProxyRoute } from '@goblin/shared';

const BACKEND_URL = resolveBackendOrigin();

const INTERNAL_PROXY_API_KEY = (
  process.env['INTERNAL_PROXY_API_KEY'] ||
  process.env['BACKEND_API_KEY'] ||
  process.env['INTERNAL_API_SECRET'] ||
  ''
).trim();

type RouteContext = {
  params: Promise<{ path?: string[] | undefined }>;
};

const normalizePathname = (pathname: string): string =>
  pathname !== '/' ? pathname.replace(/\/+$/, '') : pathname;

const isPrefixMatch = (pathname: string, prefix: string): boolean =>
  pathname === prefix || pathname.startsWith(`${prefix}/`);

const pathSegmentCount = (pathname: string): number => pathname.split('/').filter(Boolean).length;

const pathSegmentsToPathname = (segments: readonly string[]): string =>
  segments.length === 0 ? '/api' : `/api/${segments.join('/')}`;

const suffixFromSegments = (segments: readonly string[], frontendPrefix: string): string => {
  const prefixSegments = Math.max(pathSegmentCount(frontendPrefix) - 1, 0);
  return segments.slice(prefixSegments).join('/');
};

export const resolveProxyRoute = (pathname: string): ApiProxyRoute | null => {
  const normalizedPathname = normalizePathname(pathname);
  let resolved: ApiProxyRoute | null = null;

  for (const route of API_PROXY_ROUTES) {
    if (!isPrefixMatch(normalizedPathname, route.frontendPrefix)) {
      continue;
    }

    if (!resolved || route.frontendPrefix.length > resolved.frontendPrefix.length) {
      resolved = route;
    }
  }

  return resolved;
};

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

async function forwardRequest(
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

async function forwardPrefixedRequest(
  req: Request,
  context: RouteContext,
  backendBasePath: string
): Promise<Response> {
  const { path = [] } = await context.params;
  return forwardRequest(req, backendBasePath, path.join('/'));
}

async function forwardResolvedProxyRequest(
  req: Request,
  pathSegments: string[]
): Promise<Response> {
  if (pathSegments.length === 0) {
    return NextResponse.json({ detail: 'Not found' }, { status: 404 });
  }

  const pathname = pathSegmentsToPathname(pathSegments);
  const resolved = resolveProxyRoute(pathname);
  if (!resolved) {
    return NextResponse.json({ detail: 'Not found' }, { status: 404 });
  }

  return forwardRequest(
    req,
    resolved.backendPrefix,
    suffixFromSegments(pathSegments, resolved.frontendPrefix)
  );
}

export function buildBackendProxyHandlers(backendBasePath: string) {
  return {
    GET(req: Request, context: RouteContext) {
      return forwardPrefixedRequest(req, context, backendBasePath);
    },
    POST(req: Request, context: RouteContext) {
      return forwardPrefixedRequest(req, context, backendBasePath);
    },
    PUT(req: Request, context: RouteContext) {
      return forwardPrefixedRequest(req, context, backendBasePath);
    },
    PATCH(req: Request, context: RouteContext) {
      return forwardPrefixedRequest(req, context, backendBasePath);
    },
    DELETE(req: Request, context: RouteContext) {
      return forwardPrefixedRequest(req, context, backendBasePath);
    },
  };
}

export function buildCatchAllProxyHandlers() {
  const handle = async (req: Request, context: RouteContext): Promise<Response> => {
    const { path = [] } = await context.params;
    return forwardResolvedProxyRequest(req, path);
  };

  return {
    GET(req: Request, context: RouteContext) {
      return handle(req, context);
    },
    POST(req: Request, context: RouteContext) {
      return handle(req, context);
    },
    PUT(req: Request, context: RouteContext) {
      return handle(req, context);
    },
    PATCH(req: Request, context: RouteContext) {
      return handle(req, context);
    },
    DELETE(req: Request, context: RouteContext) {
      return handle(req, context);
    },
  };
}
