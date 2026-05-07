jest.mock('../env', () => ({
  env: {
    features: {
      ragEnabled: true,
      multiProvider: true,
      passkeyAuth: false,
      googleAuth: true,
      orchestration: false,
      sandbox: true,
      search: true,
      admin: true,
      analytics: true,
      debugMode: false,
    },
    isDevelopment: false,
  },
}));

jest.mock('../../utils/dev-log', () => ({
  devLog: jest.fn(),
}));

import { featureFlags, moduleFlags, isFeatureEnabled, getEnabledModules } from '../features';

describe('featureFlags', () => {
  it('has ragEnabled set to true', () => {
    expect(featureFlags.ragEnabled).toBe(true);
  });

  it('has multiProvider set to true', () => {
    expect(featureFlags.multiProvider).toBe(true);
  });

  it('has passkeyAuth set to false', () => {
    expect(featureFlags.passkeyAuth).toBe(false);
  });
});

describe('moduleFlags', () => {
  it('reflects sandbox flag', () => {
    expect(moduleFlags.sandbox).toBe(true);
  });

  it('reflects search flag', () => {
    expect(moduleFlags.search).toBe(true);
  });

  it('reflects admin flag', () => {
    expect(moduleFlags.admin).toBe(true);
  });
});

describe('isFeatureEnabled', () => {
  it('returns true for enabled features', () => {
    expect(isFeatureEnabled('ragEnabled')).toBe(true);
  });

  it('returns false for disabled features', () => {
    expect(isFeatureEnabled('passkeyAuth')).toBe(false);
  });
});

describe('getEnabledModules', () => {
  it('returns module flags', () => {
    const modules = getEnabledModules();
    expect(modules.sandbox).toBe(true);
    expect(modules.search).toBe(true);
    expect(modules.admin).toBe(true);
  });
});