import { resolveStartupDestinationRoute } from '../useStartupFlow';

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
