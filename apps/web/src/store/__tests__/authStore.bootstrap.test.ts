const clearCookie = (name: string) => {
  document.cookie = `${name}=; Path=/; Max-Age=0`;
};

const setCookie = (name: string, value: string) => {
  document.cookie = `${name}=${encodeURIComponent(value)}; Path=/`;
};

jest.mock('@/lib/api', () => ({
  apiClient: {
    validateToken: jest.fn(),
  },
}));

describe('authStore bootstrapFromSession', () => {
  beforeEach(() => {
    jest.resetModules();
    localStorage.clear();
    clearCookie('session_token');
    clearCookie('goblin_auth');
    clearCookie('goblin_admin');
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('hydrates token from cookie and validates via /api/auth/validate', async () => {
    setCookie('session_token', 'cookie-token-123');
    localStorage.setItem(
      'user_data',
      JSON.stringify({ id: 'u1', email: 'u1@example.com', role: 'user' })
    );

    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { apiClient } = require('@/lib/api') as typeof import('@/lib/api');
    (apiClient.validateToken as jest.Mock).mockResolvedValue({
      valid: true,
      user: { id: 'u1', email: 'u1@example.com', role: 'user' },
    });

    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { useAuthStore } = require('../authStore') as typeof import('../authStore');
    await useAuthStore.getState().bootstrapFromSession();

    const state = useAuthStore.getState();
    expect(state.token).toBe('cookie-token-123');
    expect(state.isAuthenticated).toBe(true);
    expect(state.isHydrated).toBe(true);
    expect(apiClient.validateToken).toHaveBeenCalledTimes(1);
    expect(apiClient.validateToken).toHaveBeenCalledWith('cookie-token-123');
  });

  it('clears session on hard auth denial (401)', async () => {
    setCookie('session_token', 'cookie-token-401');
    localStorage.setItem(
      'user_data',
      JSON.stringify({ id: 'u401', email: 'u401@example.com', role: 'user' })
    );

    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { apiClient } = require('@/lib/api') as typeof import('@/lib/api');
    const authError = new Error('Invalid authentication') as Error & { status?: number };
    authError.status = 401;
    (apiClient.validateToken as jest.Mock).mockRejectedValue(authError);

    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { useAuthStore } = require('../authStore') as typeof import('../authStore');
    await useAuthStore.getState().bootstrapFromSession();

    const state = useAuthStore.getState();
    expect(state.token).toBeNull();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(state.isHydrated).toBe(true);
  });

  it('keeps provisional session on transient validation failure', async () => {
    setCookie('session_token', 'cookie-token-503');
    localStorage.setItem(
      'user_data',
      JSON.stringify({ id: 'u503', email: 'u503@example.com', role: 'user' })
    );

    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { apiClient } = require('@/lib/api') as typeof import('@/lib/api');
    const transientError = new Error('backend unavailable') as Error & { status?: number };
    transientError.status = 503;
    (apiClient.validateToken as jest.Mock).mockRejectedValue(transientError);

    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { useAuthStore } = require('../authStore') as typeof import('../authStore');
    await useAuthStore.getState().bootstrapFromSession();

    const state = useAuthStore.getState();
    expect(state.token).toBe('cookie-token-503');
    expect(state.isAuthenticated).toBe(true);
    expect(state.isHydrated).toBe(true);
  });

  it('clears session when backend explicitly returns valid:false', async () => {
    setCookie('session_token', 'cookie-token-invalid');
    localStorage.setItem(
      'user_data',
      JSON.stringify({ id: 'uinvalid', email: 'uinvalid@example.com', role: 'user' })
    );

    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { apiClient } = require('@/lib/api') as typeof import('@/lib/api');
    (apiClient.validateToken as jest.Mock).mockResolvedValue({ valid: false });

    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { useAuthStore } = require('../authStore') as typeof import('../authStore');
    await useAuthStore.getState().bootstrapFromSession();

    const state = useAuthStore.getState();
    expect(state.token).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(state.isHydrated).toBe(true);
  });

  it('keeps a provisional session when user_data is malformed but token validates', async () => {
    setCookie('session_token', 'cookie-token-malformed');
    localStorage.setItem('user_data', '{not-json');

    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { apiClient } = require('@/lib/api') as typeof import('@/lib/api');
    (apiClient.validateToken as jest.Mock).mockResolvedValue({
      valid: true,
      user: { id: 'u2', email: 'u2@example.com', role: 'user' },
    });

    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { useAuthStore } = require('../authStore') as typeof import('../authStore');
    await useAuthStore.getState().bootstrapFromSession();

    const state = useAuthStore.getState();
    expect(state.token).toBe('cookie-token-malformed');
    expect(state.user).toEqual(expect.objectContaining({ id: 'u2' }));
    expect(state.isAuthenticated).toBe(true);
    expect(state.isHydrated).toBe(true);
  });

  it('marks hydrated without auth when no token and no auth cookie exist', async () => {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { useAuthStore } = require('../authStore') as typeof import('../authStore');
    await useAuthStore.getState().bootstrapFromSession();

    const state = useAuthStore.getState();
    expect(state.token).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(state.isHydrated).toBe(true);
  });

  it('hydrates without auth when only the auth cookie exists', async () => {
    setCookie('goblin_auth', 'true');

    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { useAuthStore } = require('../authStore') as typeof import('../authStore');
    await useAuthStore.getState().bootstrapFromSession();

    const state = useAuthStore.getState();
    expect(state.token).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(state.isHydrated).toBe(true);
  });

  it('falls back to stored user when validate response is missing a usable user', async () => {
    setCookie('session_token', 'cookie-token-fallback');
    localStorage.setItem(
      'user_data',
      JSON.stringify({ id: 'ufallback', email: 'fallback@example.com', role: 'admin' })
    );

    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { apiClient } = require('@/lib/api') as typeof import('@/lib/api');
    (apiClient.validateToken as jest.Mock).mockResolvedValue({ valid: true, user: null });

    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { useAuthStore } = require('../authStore') as typeof import('../authStore');
    await useAuthStore.getState().bootstrapFromSession();

    const state = useAuthStore.getState();
    expect(state.user).toEqual(expect.objectContaining({ id: 'ufallback' }));
    expect(state.isAuthenticated).toBe(true);
  });

  it('does not authenticate when validate response user object is invalid', async () => {
    setCookie('session_token', 'cookie-token-invalid-user');
    localStorage.setItem(
      'user_data',
      JSON.stringify({ email: 'no-id@example.com', role: 'user' })
    );

    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { apiClient } = require('@/lib/api') as typeof import('@/lib/api');
    (apiClient.validateToken as jest.Mock).mockResolvedValue({
      valid: true,
      user: { email: 'bad@example.com' },
    });

    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { useAuthStore } = require('../authStore') as typeof import('../authStore');
    await useAuthStore.getState().bootstrapFromSession();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.isHydrated).toBe(true);
  });

  it('supports setSession clearSession hasRole and hasAnyRole', () => {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { useAuthStore } = require('../authStore') as typeof import('../authStore');

    useAuthStore.getState().setSession({
      token: 'token-1',
      refreshToken: 'refresh-1',
      user: {
        id: 'u-role',
        email: 'role@example.com',
        role: 'admin',
        roles: ['admin', 'editor'],
      },
      expiresIn: 3600,
    });

    let state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.hasRole('admin')).toBe(true);
    expect(state.hasRole('user')).toBe(false);
    expect(state.hasAnyRole(['viewer', 'editor'])).toBe(true);
    expect(state.hasAnyRole([])).toBe(false);

    state.clearSession();
    state = useAuthStore.getState();
    expect(state.token).toBeNull();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });
});
