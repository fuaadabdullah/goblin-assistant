import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { createSupabaseMiddlewareClient } from './src/lib/supabase-server';
import { isAdminUser } from './src/utils/access';
import { hasSessionCookie, isAdminCookie, resolveRouteDecision } from './src/server/route-protection';

const isLocalhost = (hostname: string): boolean =>
  hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1';

export async function proxy(request: NextRequest) {
  const { supabase, getResponse } = createSupabaseMiddlewareClient(request);
  const e2eAuthBypass =
    isLocalhost(request.nextUrl.hostname) && request.cookies.get('goblin_e2e_auth')?.value === '1';

  // getUser() validates the session server-side and refreshes the token if
  // needed. We intentionally call this (not getSession()) so the proxy
  // never trusts a stale cached value.
  const user = e2eAuthBypass ? null : (await supabase.auth.getUser()).data.user;

  const decision = resolveRouteDecision({
    pathname: request.nextUrl.pathname,
    search: request.nextUrl.search,
    isAuthenticated: e2eAuthBypass || hasSessionCookie(request) || Boolean(user),
    isAdmin: isAdminCookie(request) || isAdminUser(user ?? null),
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
    '/debug/connectivity/:path*',
  ],
};
