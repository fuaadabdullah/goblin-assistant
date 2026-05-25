import { jest } from '@jest/globals';

describe('feature flags config', () => {
  const originalEnv = process.env;
  const devLogMock = jest.fn();

  const loadFeaturesModule = (overrides: Partial<{
    isDevelopment: boolean;
    featureFlags: Record<string, boolean>;
  }> = {}) => {
    jest.doMock('../env', () => ({
      __esModule: true,
      env: {
        isDevelopment: overrides.isDevelopment ?? false,
        features: {
          ragEnabled: true,
          multiProvider: false,
          passkeyAuth: true,
          googleAuth: false,
          orchestration: true,
          sandbox: false,
          search: true,
          admin: false,
          analytics: true,
          debugMode: false,
          ...(overrides.featureFlags || {}),
        },
      },
    }));

    jest.doMock('../../utils/dev-log', () => ({
      __esModule: true,
      devLog: devLogMock,
    }));

    return require('../features') as typeof import('../features');
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

  it('maps feature flags to module flags and checks feature state', () => {
    const { featureFlags, moduleFlags, isFeatureEnabled, getEnabledModules } = loadFeaturesModule();

    expect(featureFlags.ragEnabled).toBe(true);
    expect(featureFlags.multiProvider).toBe(false);
    expect(featureFlags.passkeyAuth).toBe(true);
    expect(featureFlags.search).toBe(true);
    expect(featureFlags.admin).toBe(false);

    expect(moduleFlags).toEqual({
      sandbox: false,
      search: true,
      admin: false,
    });
    expect(getEnabledModules()).toBe(moduleFlags);
    expect(isFeatureEnabled('search')).toBe(true);
    expect(isFeatureEnabled('admin')).toBe(false);
  });

  it('logs feature flags in development when debug mode is enabled', () => {
    loadFeaturesModule({
      isDevelopment: true,
      featureFlags: {
        debugMode: true,
      },
    });

    expect(devLogMock).toHaveBeenCalledWith(
      '🚩 Feature Flags:',
      expect.objectContaining({
        debugMode: true,
      }),
    );
  });
});