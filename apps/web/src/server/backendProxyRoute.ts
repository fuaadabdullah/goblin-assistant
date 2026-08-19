import { type NextRequest, NextResponse } from 'next/server';
import { forwardRequest } from './proxy/httpForwarder';
import {
  pathSegmentsToPathname,
  resolveProxyRoute,
  suffixFromSegments,
} from './proxy/routeResolver';

export { resolveProxyRoute } from './proxy/routeResolver';

// Next.js 16 route handlers receive params as Promise<unknown>; we cast after awaiting.
type RouteContext = { params: Promise<unknown> };
type PathParams = { path?: string[] | undefined };

async function forwardPrefixedRequest(
  req: NextRequest,
  context: RouteContext,
  backendBasePath: string
): Promise<Response> {
  const { path = [] } = (await context.params) as PathParams;
  return forwardRequest(req, backendBasePath, path.join('/'));
}

async function forwardResolvedProxyRequest(
  req: NextRequest,
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
    GET(req: NextRequest, context: RouteContext) {
      return forwardPrefixedRequest(req, context, backendBasePath);
    },
    POST(req: NextRequest, context: RouteContext) {
      return forwardPrefixedRequest(req, context, backendBasePath);
    },
    PUT(req: NextRequest, context: RouteContext) {
      return forwardPrefixedRequest(req, context, backendBasePath);
    },
    PATCH(req: NextRequest, context: RouteContext) {
      return forwardPrefixedRequest(req, context, backendBasePath);
    },
    DELETE(req: NextRequest, context: RouteContext) {
      return forwardPrefixedRequest(req, context, backendBasePath);
    },
  };
}

export function buildCatchAllProxyHandlers() {
  const handle = async (req: NextRequest, context: RouteContext): Promise<Response> => {
    const { path = [] } = (await context.params) as PathParams;
    return forwardResolvedProxyRequest(req, path);
  };

  return {
    GET(req: NextRequest, context: RouteContext) {
      return handle(req, context);
    },
    POST(req: NextRequest, context: RouteContext) {
      return handle(req, context);
    },
    PUT(req: NextRequest, context: RouteContext) {
      return handle(req, context);
    },
    PATCH(req: NextRequest, context: RouteContext) {
      return handle(req, context);
    },
    DELETE(req: NextRequest, context: RouteContext) {
      return handle(req, context);
    },
  };
}
