import { jest } from '@jest/globals';

describe('env config', () => {
  const originalEnv = process.env;
  const devLogMock = jest.fn();
  const devWarnMock = jest.fn();
  const devErrorMock = jest.fn();

  const mockDevLogModule = () => {
    jest.doMock('../../utils/dev-log', () => ({
      __esModule: true,
      devLog: devLogMock,
      devWarn: devWarnMock,
      devError: devErrorMock,
    }));
  };

  const loadEnvModule = () => {
    mockDevLogModule();
    return require('../env') as typeof import('../env');
  };

  beforeEach(() => {
    jest.resetModules();
    jest.clearAllMocks();
    process.env = {
      ...originalEnv,
      NODE_ENV: 'development',
      NEXT_PUBLIC_API_BASE_URL: 'https://api.example.com',
      NEXT_PUBLIC_BACKEND_URL: 'https://backend.example.com',
      NEXT_PUBLIC_FASTAPI_URL: 'https://fastapi.example.com',
      NEXT_PUBLIC_ENABLE_DEBUG: 'true',
      NEXT_PUBLIC_FEATURE_RAG_ENABLED: 'true',
      NEXT_PUBLIC_FEATURE_MULTI_PROVIDER: 'true',
      NEXT_PUBLIC_FEATURE_PASSKEY_AUTH: 'false',
      NEXT_PUBLIC_FEATURE_GOOGLE_AUTH: 'true',
      NEXT_PUBLIC_FEATURE_ORCHESTRATION: 'false',
      NEXT_PUBLIC_FEATURE_SANDBOX: 'true',
      NEXT_PUBLIC_FEATURE_SEARCH: 'false',
      NEXT_PUBLIC_FEATURE_ADMIN: 'true',
      NEXT_PUBLIC_ENABLE_ANALYTICS: 'true',
      NEXT_PUBLIC_DEBUG_MODE: 'true',
      NEXT_PUBLIC_TURNSTILE_SITE_KEY_CHAT: '0xchat-key',
      NEXT_PUBLIC_TURNSTILE_SITE_KEY_LOGIN: '0xlogin-key',
      NEXT_PUBLIC_TURNSTILE_SITE_KEY_SEARCH: '0xsearch-key',
      NEXT_PUBLIC_SENTRY_DSN: 'https://dsn.example.com',
      NEXT_PUBLIC_GA_MEASUREMENT_ID: 'G-TEST123',
    };
  });

  afterEach(() => {
    process.env = originalEnv;
    jest.dontMock('../../utils/dev-log');
  });

  it('exports validated environment values and logs in development', () => {
    const { env } = loadEnvModule();

    expect(env.apiBaseUrl).toBe('https://api.example.com');
    expect(env.backendUrl).toBe('https://backend.example.com');
    expect(env.fastApiUrl).toBe('https://fastapi.example.com');
    expect(env.enableDebug).toBe(true);
    expect(env.features.ragEnabled).toBe(true);
    expect(env.features.multiProvider).toBe(true);
    expect(env.features.passkeyAuth).toBe(false);
    expect(env.features.googleAuth).toBe(true);
    expect(env.features.orchestration).toBe(false);
    expect(env.features.sandbox).toBe(true);
    expect(env.features.search).toBe(false);
    expect(env.features.admin).toBe(true);
    expect(env.features.analytics).toBe(true);
    expect(env.features.debugMode).toBe(true);
    expect(env.turnstile.chat).toBe('0xchat-key');
    expect(env.turnstile.login).toBe('0xlogin-key');
    expect(env.turnstile.search).toBe('0xsearch-key');
    expect(env.mode).toBe('development');
    expect(env.isDevelopment).toBe(true);
    expect(env.isProduction).toBe(false);
    expect(devLogMock).toHaveBeenCalled();
  });

  it('throws when the api base url is invalid', () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = 'not-a-url';

    expect(() => loadEnvModule()).toThrow('Invalid environment configuration');
    expect(devErrorMock).toHaveBeenCalled();
  });

  it('throws when a turnstile key has an invalid format', () => {
    process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY_CHAT = 'invalid-key';

    expect(() => loadEnvModule()).toThrow('Invalid environment configuration');
    expect(devErrorMock).toHaveBeenCalled();
  });
});
