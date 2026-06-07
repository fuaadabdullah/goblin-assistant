describe('turnstile config', () => {
  const originalEnv = process.env;
  const devWarnMock = vi.fn();
  const devErrorMock = vi.fn();

  const loadTurnstileModule = async (
    overrides: Partial<{
      chat: string;
      login: string;
      search: string;
    }> = {}
  ) => {
    vi.doMock('../env', () => ({
      env: {
        turnstile: {
          chat: '0xchat-key',
          login: '0xlogin-key',
          search: '0xsearch-key',
          ...overrides,
        },
      },
    }));

    vi.doMock('../../utils/dev-log', () => ({
      devWarn: devWarnMock,
      devError: devErrorMock,
    }));

    return import('../turnstile') as Promise<typeof import('../turnstile')>;
  };

  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
    vi.unmock('../env');
    vi.unmock('../../utils/dev-log');
  });

  it('builds config for enabled contexts', async () => {
    const { TURNSTILE_CONFIG, useTurnstile } = await loadTurnstileModule();

    expect(TURNSTILE_CONFIG.chat).toEqual({ siteKey: '0xchat-key', enabled: true });
    expect(TURNSTILE_CONFIG.login).toEqual({ siteKey: '0xlogin-key', enabled: true });
    expect(TURNSTILE_CONFIG.search).toEqual({ siteKey: '0xsearch-key', enabled: true });
    expect(useTurnstile('login')).toEqual({ siteKey: '0xlogin-key', enabled: true });
    expect(devWarnMock).not.toHaveBeenCalled();
  });

  it('warns when a context is disabled', async () => {
    const { useTurnstile } = await loadTurnstileModule({ login: '' });
    expect(useTurnstile('login')).toEqual({ siteKey: '', enabled: false });
    expect(devWarnMock).toHaveBeenCalledWith('Turnstile not configured for login');
  });

  it('throws when a key has an invalid format', async () => {
    await expect(loadTurnstileModule({ chat: 'bad-key' })).rejects.toThrow(
      'Invalid Turnstile configuration'
    );
    expect(devErrorMock).toHaveBeenCalled();
  });

  it('throws when a secret key leaks into client config', async () => {
    await expect(loadTurnstileModule({ search: '0xsecret-value' })).rejects.toThrow(
      'Security violation: Secret key in client'
    );
    expect(devErrorMock).toHaveBeenCalled();
  });
});
