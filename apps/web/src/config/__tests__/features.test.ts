describe('feature flags config', () => {
  const originalEnv = process.env;
  const devWarnMock = vi.fn();

  const loadFeaturesModule = async (
    overrides: Partial<{
      isDevelopment: boolean;
      featureFlags: Record<string, boolean>;
    }> = {}
  ) => {
    vi.doMock('../env', () => ({
      env: {
        isDevelopment: overrides.isDevelopment ?? false,
        features: {
          ragEnabled: true,
          multiProvider: false,
          passkeyAuth: true,
          googleAuth: false,
          sandbox: false,
          search: true,
          admin: false,
          debugMode: false,
          ...(overrides.featureFlags || {}),
        },
      },
    }));

    vi.doMock('../../utils/dev-log', () => ({
      devWarn: devWarnMock,
    }));

    return import('../features') as Promise<typeof import('../features')>;
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

  it('maps feature flags to module flags and checks feature state', async () => {
    const { featureFlags, moduleFlags, isFeatureEnabled, getEnabledModules } =
      await loadFeaturesModule();

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

  it('logs feature flags in development when debug mode is enabled', async () => {
    await loadFeaturesModule({
      isDevelopment: true,
      featureFlags: { debugMode: true },
    });

    expect(devWarnMock).toHaveBeenCalledWith(
      '🚩 Feature Flags:',
      expect.objectContaining({ debugMode: true })
    );
  });
});
