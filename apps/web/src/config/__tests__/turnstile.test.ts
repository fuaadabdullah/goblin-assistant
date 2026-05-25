import { jest } from '@jest/globals';

describe('turnstile config', () => {
  const originalEnv = process.env;
  const devWarnMock = jest.fn();
  const devErrorMock = jest.fn();

  const loadTurnstileModule = (overrides: Partial<{
    chat: string;
    login: string;
    search: string;
  }> = {}) => {
    jest.doMock('../env', () => ({
      __esModule: true,
      env: {
        turnstile: {
          chat: '0xchat-key',
          login: '0xlogin-key',
          search: '0xsearch-key',
          ...overrides,
        },
      },
    }));

    jest.doMock('../../utils/dev-log', () => ({
      __esModule: true,
      devWarn: devWarnMock,
      devError: devErrorMock,
    }));

    return require('../turnstile') as typeof import('../turnstile');
  };

  beforeEach(() => {
    jest.resetModules();
    jest.clearAllMocks();
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
    jest.dontMock('../env');
    jest.dontMock('../../utils/dev-log');
  });

  it('builds config for enabled contexts', () => {
    const { TURNSTILE_CONFIG, useTurnstile } = loadTurnstileModule();

    expect(TURNSTILE_CONFIG.chat).toEqual({
      siteKey: '0xchat-key',
      enabled: true,
    });
    expect(TURNSTILE_CONFIG.login).toEqual({
      siteKey: '0xlogin-key',
      enabled: true,
    });
    expect(TURNSTILE_CONFIG.search).toEqual({
      siteKey: '0xsearch-key',
      enabled: true,
    });

    expect(useTurnstile('login')).toEqual({
      siteKey: '0xlogin-key',
      enabled: true,
    });
    expect(devWarnMock).not.toHaveBeenCalled();
  });

  it('warns when a context is disabled', () => {
    const { useTurnstile } = loadTurnstileModule({
      login: '',
    });

    expect(useTurnstile('login')).toEqual({
      siteKey: '',
      enabled: false,
    });
    expect(devWarnMock).toHaveBeenCalledWith('Turnstile not configured for login');
  });

  it('throws when a key has an invalid format', () => {
    expect(() => loadTurnstileModule({ chat: 'bad-key' })).toThrow('Invalid Turnstile configuration');
    expect(devErrorMock).toHaveBeenCalled();
  });

  it('throws when a secret key leaks into client config', () => {
    expect(() => loadTurnstileModule({ search: '0xsecret-value' })).toThrow(
      'Security violation: Secret key in client',
    );
    expect(devErrorMock).toHaveBeenCalled();
  });
});
