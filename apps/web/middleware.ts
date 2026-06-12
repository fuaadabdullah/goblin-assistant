import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { createSupabaseMiddlewareClient } from './src/lib/supabase-server';
import { isAdminUser } from './src/utils/access';

/**
 * Auth middleware for route protection.
 *
 * Uses @supabase/ssr to read the Supabase session from cookies directly —
 * no goblin_auth flag cookie needed. Calling getUser() also transparently
 * refreshes the access token when it's close to expiry, and the updated
 * cookies are forwarded to the browser via the returned response object.
 */

const AUTH_ROUTE_PREFIXES = ['/chat', '/account', '/settings', '/search'] as const;
const ADMIN_ROUTE_PREFIXES = ['/admin'] as const;

const matchesPrefix = (pathname: string, prefixes: readonly string[]): boolean =>
  prefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));

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

  const isGuestChatAllowed =
    input.pathname.startsWith('/chat') &&
    new URLSearchParams(input.search || '').get('guest') === '1';

  if (requiresAuth && !input.isAuthenticated && !isGuestChatAllowed) {
    return {
      allow: false,
      redirectTarget: `${input.pathname}${input.search || ''}`,
    };
  }

  return { allow: true };
};

export async function middleware(request: NextRequest) {
  const { supabase, getResponse } = createSupabaseMiddlewareClient(request);

  // getUser() validates the session server-side and refreshes the token if
  // needed. We intentionally call this (not getSession()) so the middleware
  // never trusts a stale cached value.
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const decision = resolveRouteDecision({
    pathname: request.nextUrl.pathname,
    search: request.nextUrl.search,
    isAuthenticated: Boolean(user),
    isAdmin: isAdminUser(user ?? null),
  });

  if (!decision.allow) {
    const url = request.nextUrl.clone();
    url.pathname = '/login';
    url.search = '';
    url.searchParams.set('redirect', decision.redirectTarget || '/');
    return NextResponse.redirect(url);
  }

  // Return the response from createSupabaseMiddlewareClient so refreshed
  // session cookies are forwarded to the browser.
  return getResponse();
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
