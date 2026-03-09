import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Auth middleware for route protection.
 *
 * Current model: The backend issues a JWT on login. The client stores it in
 * localStorage (not accessible here) and sets a `goblin_auth=1` cookie flag so
 * this Edge middleware can gate protected routes without needing a JWT library.
 *
 * Security note: The cookie flag is a *convenience gate*, not a security
 * boundary. All sensitive data fetches still require a valid JWT in the
 * Authorization header, validated server-side. A user who manually sets the
 * cookie will only see empty/errored pages — they cannot access data.
 */

export const AUTH_COOKIE_NAME = 'goblin_auth';
export const ADMIN_COOKIE_NAME = 'goblin_admin';
export const SESSION_TOKEN_COOKIE = 'session_token';

const AUTH_ROUTE_PREFIXES = ['/chat', '/account', '/settings', '/search'] as const;
const ADMIN_ROUTE_PREFIXES = ['/admin'] as const;

const matchesPrefix = (pathname: string, prefixes: readonly string[]): boolean =>
  prefixes.some(prefix => pathname === prefix || pathname.startsWith(`${prefix}/`));

/**
 * Check for authentication presence.
 *
 * IMPORTANT: We now require a plausible `session_token` cookie for protected
 * routes. The legacy `goblin_auth=1` flag alone is insufficient because it can
 * become stale or be manually set, leading to route-bypass UX.
 */
const hasAuthCookie = (request: NextRequest): boolean => {
  const sessionToken = request.cookies.get(SESSION_TOKEN_COOKIE)?.value;
  return Boolean(sessionToken && sessionToken.length > 10);
};

const isAdmin = (request: NextRequest): boolean => {
  return request.cookies.get(ADMIN_COOKIE_NAME)?.value === '1';
};

export interface RouteDecision {
  allow: boolean;
  redirectTarget?: string;
}

export const resolveRouteDecision = (input: {
  pathname: string;
  search?: string;
  isAuthenticated: boolean;
  isAdmin: boolean;
}): RouteDecision => {
  const requiresAdmin = matchesPrefix(input.pathname, ADMIN_ROUTE_PREFIXES);
  const requiresAuth = requiresAdmin || matchesPrefix(input.pathname, AUTH_ROUTE_PREFIXES);

  if (requiresAdmin && (!input.isAuthenticated || !input.isAdmin)) {
    return {
      allow: false,
      redirectTarget: `${input.pathname}${input.search || ''}`,
    };
  }

  if (requiresAuth && !input.isAuthenticated) {
    return {
      allow: false,
      redirectTarget: `${input.pathname}${input.search || ''}`,
    };
  }

  return { allow: true };
};

export function middleware(request: NextRequest) {
  const decision = resolveRouteDecision({
    pathname: request.nextUrl.pathname,
    search: request.nextUrl.search,
    isAuthenticated: hasAuthCookie(request),
    isAdmin: isAdmin(request),
  });

  if (!decision.allow) {
    const url = request.nextUrl.clone();
    url.pathname = '/login';
    url.search = '';
    url.searchParams.set('redirect', decision.redirectTarget || '/');
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/chat/:path*',
    '/account/:path*',
    '/settings/:path*',
    '/search/:path*',
    '/admin/:path*',
  ],
};
