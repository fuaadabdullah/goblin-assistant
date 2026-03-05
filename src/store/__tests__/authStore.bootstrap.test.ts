const clearCookie = (name: string) => {
  document.cookie = `${name}=; Path=/; Max-Age=0`;
};

const setCookie = (name: string, value: string) => {
  document.cookie = `${name}=${encodeURIComponent(value)}; Path=/`;
};

const createFetchResponse = (status: number, body: unknown): Response =>
  ({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as unknown as Response);

describe('authStore bootstrapFromSession', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    jest.resetModules();
    localStorage.clear();
    clearCookie('session_token');
    clearCookie('goblin_auth');
    clearCookie('goblin_admin');
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it('hydrates token from cookie and validates via /api/auth/validate', async () => {
    setCookie('session_token', 'cookie-token-123');
    localStorage.setItem(
      'user_data',
      JSON.stringify({ id: 'u1', email: 'u1@example.com', role: 'user' }),
    );

    const fetchMock = jest
      .fn()
      .mockResolvedValue(
        createFetchResponse(200, {
          valid: true,
          user: { id: 'u1', email: 'u1@example.com', role: 'user' },
        }),
      );
    global.fetch = fetchMock as unknown as typeof fetch;

    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { useAuthStore } = require('../authStore') as typeof import('../authStore');
    await useAuthStore.getState().bootstrapFromSession();

    const state = useAuthStore.getState();
    expect(state.token).toBe('cookie-token-123');
    expect(state.isAuthenticated).toBe(true);
    expect(state.isHydrated).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe('/api/auth/validate');
    expect(fetchMock.mock.calls[0][1]).toEqual(
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Authorization: 'Bearer cookie-token-123',
        }),
      }),
    );
  });

  it('clears session on hard auth denial (401)', async () => {
    setCookie('session_token', 'cookie-token-401');
    localStorage.setItem(
      'user_data',
      JSON.stringify({ id: 'u401', email: 'u401@example.com', role: 'user' }),
    );

    const fetchMock = jest
      .fn()
      .mockResolvedValue(createFetchResponse(401, { detail: 'Invalid authentication' }));
    global.fetch = fetchMock as unknown as typeof fetch;

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
      JSON.stringify({ id: 'u503', email: 'u503@example.com', role: 'user' }),
    );

    const fetchMock = jest
      .fn()
      .mockResolvedValue(createFetchResponse(503, { error: 'backend unavailable' }));
    global.fetch = fetchMock as unknown as typeof fetch;

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
      JSON.stringify({ id: 'uinvalid', email: 'uinvalid@example.com', role: 'user' }),
    );

    const fetchMock = jest
      .fn()
      .mockResolvedValue(createFetchResponse(200, { valid: false }));
    global.fetch = fetchMock as unknown as typeof fetch;

    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { useAuthStore } = require('../authStore') as typeof import('../authStore');
    await useAuthStore.getState().bootstrapFromSession();

    const state = useAuthStore.getState();
    expect(state.token).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(state.isHydrated).toBe(true);
  });
});
