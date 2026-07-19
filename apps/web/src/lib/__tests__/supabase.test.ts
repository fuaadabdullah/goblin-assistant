const { createBrowserClientMock, authMocks, unsubscribeMock } = vi.hoisted(() => {
  const unsubscribeMock = vi.fn();
  const authMocks = {
    signUp: vi.fn(),
    signInWithPassword: vi.fn(),
    signInWithOAuth: vi.fn(),
    getSession: vi.fn(),
    updateUser: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn(),
    exchangeCodeForSession: vi.fn(),
    onAuthStateChange: vi.fn(),
  };
  const client = { auth: authMocks };
  return {
    createBrowserClientMock: vi.fn(() => client),
    authMocks,
    unsubscribeMock,
  };
});

vi.mock('@supabase/ssr', () => ({
  createBrowserClient: createBrowserClientMock,
}));

vi.mock('../utils/dev-log', () => ({
  devWarn: vi.fn(),
}));

describe('supabase helpers', () => {
  const originalEnv = process.env;

  const loadModule = async () => {
    vi.resetModules();
    process.env = {
      ...originalEnv,
      NEXT_PUBLIC_SUPABASE_URL: 'https://supabase.test',
      NEXT_PUBLIC_SUPABASE_ANON_KEY: 'anon-key',
    };
    return import('../supabase') as Promise<typeof import('../supabase')>;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it('maps Supabase users into app users and wraps auth methods', async () => {
    const mod = await loadModule();

    expect(mod.supabaseConfigured).toBe(true);
    expect(createBrowserClientMock).toHaveBeenCalledWith('https://supabase.test', 'anon-key', {
      realtime: { params: { eventsPerSecond: 10 } },
    });

    expect(
      mod.supabaseUserToAppUser({
        id: 'u1',
        email: 'user@example.com',
        user_metadata: { name: 'User One' },
        role: undefined,
        created_at: '2026-07-17T00:00:00Z',
      })
    ).toEqual({
      id: 'u1',
      email: 'user@example.com',
      name: 'User One',
      role: 'authenticated',
      created_at: '2026-07-17T00:00:00Z',
    });

    authMocks.signUp.mockResolvedValue({
      data: { session: { access_token: 'signup-session' } },
      error: null,
    });
    authMocks.signInWithPassword.mockResolvedValue({
      data: { session: { access_token: 'signin-session' } },
      error: null,
    });
    authMocks.signInWithOAuth.mockResolvedValue({
      data: { url: 'https://oauth.example/login' },
      error: null,
    });
    authMocks.getSession.mockResolvedValue({
      data: { session: { access_token: 'session-token' } },
      error: null,
    });
    authMocks.updateUser.mockResolvedValue({
      data: { user: { id: 'u1' } },
      error: null,
    });
    authMocks.signOut.mockResolvedValue({ error: null });
    authMocks.refreshSession.mockResolvedValue({
      data: { session: { access_token: 'refreshed-token' } },
      error: null,
    });
    authMocks.exchangeCodeForSession.mockResolvedValue({
      data: { session: { access_token: 'exchange-token' } },
      error: null,
    });
    authMocks.onAuthStateChange.mockImplementation((callback) => {
      callback('SIGNED_IN', {
        access_token: 'state-token',
        user: {
          id: 'u1',
          email: 'user@example.com',
          created_at: '2026-07-17T00:00:00Z',
        },
      } as never);
      return {
        data: {
          subscription: {
            unsubscribe: unsubscribeMock,
          },
        },
      };
    });

    await expect(mod.authSignUp('user@example.com', 'pw', 'captcha')).resolves.toEqual({
      session: { access_token: 'signup-session' },
      error: null,
    });
    expect(authMocks.signUp).toHaveBeenCalledWith({
      email: 'user@example.com',
      password: 'pw',
      options: { captchaToken: 'captcha' },
    });

    await expect(mod.authSignIn('user@example.com', 'pw')).resolves.toEqual({
      session: { access_token: 'signin-session' },
      error: null,
    });
    expect(authMocks.signInWithPassword).toHaveBeenCalledWith({
      email: 'user@example.com',
      password: 'pw',
    });

    await expect(
      mod.authSignInWithOAuth('google', 'https://app.example/callback')
    ).resolves.toEqual({
      data: { url: 'https://oauth.example/login' },
      error: null,
    });
    expect(authMocks.signInWithOAuth).toHaveBeenCalledWith({
      provider: 'google',
      options: { redirectTo: 'https://app.example/callback', scopes: 'openid email' },
    });

    await expect(mod.authGetSession()).resolves.toEqual({
      session: { access_token: 'session-token' },
      error: null,
    });
    expect(authMocks.getSession).toHaveBeenCalledTimes(1);

    await expect(mod.authUpdateUser({ email: 'new@example.com' })).resolves.toEqual({
      user: { id: 'u1' },
      error: null,
    });
    expect(authMocks.updateUser).toHaveBeenCalledWith({ email: 'new@example.com' });

    await expect(mod.authSignOut()).resolves.toEqual({ error: null });
    expect(authMocks.signOut).toHaveBeenCalledTimes(1);

    await expect(mod.authRefreshSession()).resolves.toEqual({
      session: { access_token: 'refreshed-token' },
      error: null,
    });
    expect(authMocks.refreshSession).toHaveBeenCalledTimes(1);

    await expect(mod.authExchangeCodeForSession('code-123')).resolves.toEqual({
      session: { access_token: 'exchange-token' },
      error: null,
    });
    expect(authMocks.exchangeCodeForSession).toHaveBeenCalledWith('code-123');

    const onChange = vi.fn();
    const unsubscribe = mod.authOnStateChange(onChange);
    expect(onChange).toHaveBeenCalledWith(
      'SIGNED_IN',
      expect.objectContaining({ access_token: 'state-token' })
    );
    unsubscribe();
    expect(unsubscribeMock).toHaveBeenCalledTimes(1);
  });
});
