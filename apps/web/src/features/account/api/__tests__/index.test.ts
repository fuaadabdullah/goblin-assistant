import { beforeEach, describe, expect, it, vi } from 'vitest';

const { mockApiClient } = vi.hoisted(() => ({
  mockApiClient: {
    saveAccountProfile: vi.fn(),
    saveAccountPreferences: vi.fn(),
    getAccountPreferences: vi.fn(),
  },
}));

vi.mock('@/lib/api', () => ({
  apiClient: mockApiClient,
}));

import { saveProfile } from '../index';

describe('account api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiClient.saveAccountProfile.mockResolvedValue(undefined);
    mockApiClient.saveAccountPreferences.mockResolvedValue(undefined);
    mockApiClient.getAccountPreferences.mockResolvedValue(null);
  });

  it('preserves backend profile save messages when present', async () => {
    mockApiClient.saveAccountProfile.mockRejectedValueOnce(new Error('Profile update blocked'));

    await expect(saveProfile({ name: 'Alice' })).rejects.toMatchObject({
      code: 'ACCOUNT_PROFILE_SAVE_FAILED',
      userMessage: 'Profile update blocked',
    });
  });

  it('preserves non-Error profile save failures', async () => {
    mockApiClient.saveAccountProfile.mockRejectedValueOnce('profile service unavailable');

    await expect(saveProfile({ name: 'Alice' })).rejects.toMatchObject({
      code: 'ACCOUNT_PROFILE_SAVE_FAILED',
      userMessage: 'profile service unavailable',
    });
  });

  it('saves preferences through the backend client', async () => {
    const { savePreferences } = await import('../index');

    await savePreferences({ summaries: true, notifications: false, familyMode: true });

    expect(mockApiClient.saveAccountPreferences).toHaveBeenCalledWith({
      summaries: true,
      notifications: false,
      familyMode: true,
    });
  });
});
