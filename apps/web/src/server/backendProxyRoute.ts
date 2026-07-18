import { NextResponse } from 'next/server';
import { forwardRequest } from './proxy/httpForwarder';
import { pathSegmentsToPathname, resolveProxyRoute, suffixFromSegments } from './proxy/routeResolver';

export { resolveProxyRoute } from './proxy/routeResolver';

type RouteContext = {
  params: Promise<{ path?: string[] | undefined }>;
};

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
