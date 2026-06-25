import { describe, expect, it } from 'vitest';
import { buildStartupErrorMessage, resolveStartupDestinationRoute } from '../useStartupFlow';

describe('resolveStartupDestinationRoute', () => {
  it('returns / for unauthenticated users', () => {
    expect(
      resolveStartupDestinationRoute({
        isAuthenticated: false,
        isAdmin: true,
        isAdminModuleEnabled: true,
      })
    ).toBe('/');
  });

  it('returns /chat for authenticated non-admin users', () => {
    expect(
      resolveStartupDestinationRoute({
        isAuthenticated: true,
        isAdmin: false,
        isAdminModuleEnabled: true,
      })
    ).toBe('/chat');
  });

  it('returns /admin only when authenticated and role-authorized admin module is enabled', () => {
    expect(
      resolveStartupDestinationRoute({
        isAuthenticated: true,
        isAdmin: true,
        isAdminModuleEnabled: true,
      })
    ).toBe('/admin');
  });

  it('returns /chat for admins when the admin module is disabled', () => {
    expect(
      resolveStartupDestinationRoute({
        isAuthenticated: true,
        isAdmin: true,
        isAdminModuleEnabled: false,
      })
    ).toBe('/chat');
  });
});

describe('buildStartupErrorMessage', () => {
  it('preserves underlying error messages', () => {
    expect(buildStartupErrorMessage(new Error('Auth bootstrap failed'))).toBe(
      'Auth bootstrap failed'
    );
  });

  it('falls back for unknown values', () => {
    expect(buildStartupErrorMessage('bad')).toBe(
      'We hit a snag while booting. Redirecting to help.'
    );
  });
});

