import { resolveRouteDecision } from '../../middleware';

describe('middleware route decisions', () => {
  it('redirects unauthenticated users from /chat', () => {
    const decision = resolveRouteDecision({
      pathname: '/chat',
      isAuthenticated: false,
      isAdmin: false,
    });

    expect(decision).toEqual({
      allow: false,
      redirectTarget: '/chat',
    });
  });

  it('redirects unauthenticated users from /search and preserves query string', () => {
    const decision = resolveRouteDecision({
      pathname: '/search',
      search: '?q=latest',
      isAuthenticated: false,
      isAdmin: false,
    });

    expect(decision).toEqual({
      allow: false,
      redirectTarget: '/search?q=latest',
    });
  });

  it('redirects non-admin users from /admin', () => {
    const decision = resolveRouteDecision({
      pathname: '/admin',
      isAuthenticated: true,
      isAdmin: false,
    });

    expect(decision).toEqual({
      allow: false,
      redirectTarget: '/admin',
    });
  });

  it('allows admins on /admin', () => {
    const decision = resolveRouteDecision({
      pathname: '/admin/providers',
      isAuthenticated: true,
      isAdmin: true,
    });

    expect(decision).toEqual({
      allow: true,
    });
  });

  it('does not protect /sandbox', () => {
    const decision = resolveRouteDecision({
      pathname: '/sandbox',
      isAuthenticated: false,
      isAdmin: false,
    });

    expect(decision).toEqual({
      allow: true,
    });
  });

  it('requires authentication, not just admin flag', () => {
    const decision = resolveRouteDecision({
      pathname: '/chat',
      isAuthenticated: false,
      isAdmin: true,
    });

    expect(decision).toEqual({
      allow: false,
      redirectTarget: '/chat',
    });
  });
});
