import type { NextRequest } from 'next/server';

const AUTH_ROUTE_PREFIXES = ['/chat', '/account', '/settings', '/search'] as const;
const ADMIN_ROUTE_PREFIXES = ['/admin', '/debug/connectivity'] as const;

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

export const hasSessionCookie = (request: NextRequest): boolean => {
  const sessionToken = request.cookies.get('session_token')?.value;
  return Boolean(sessionToken && sessionToken.length > 10);
};

export const isAdminCookie = (request: NextRequest): boolean =>
  request.cookies.get('goblin_admin')?.value === '1';
