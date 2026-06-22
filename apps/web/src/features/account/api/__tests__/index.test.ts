import { beforeEach, describe, expect, it, vi } from 'vitest';

const { mockAuthUpdateUser } = vi.hoisted(() => ({
  mockAuthUpdateUser: vi.fn(),
}));

vi.mock('@/lib/supabase', () => ({
  authUpdateUser: mockAuthUpdateUser,
}));

import { saveProfile } from '../index';

describe('account api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('preserves backend profile save messages when present', async () => {
    mockAuthUpdateUser.mockResolvedValueOnce({
      error: new Error('Profile update blocked'),
    });

    await expect(saveProfile({ name: 'Alice' })).rejects.toMatchObject({
      code: 'ACCOUNT_PROFILE_SAVE_FAILED',
      userMessage: 'Profile update blocked',
    });
  });

  it('preserves preferences save errors when localStorage fails', async () => {
    const setItemSpy = vi.spyOn(window.localStorage.__proto__, 'setItem').mockImplementation(() => {
      throw new Error('Quota exceeded');
    });

    const { savePreferences } = await import('../index');

    await expect(savePreferences({ summaries: true, notifications: false, familyMode: true })).rejects.toMatchObject(
      {
        code: 'ACCOUNT_PREFERENCES_SAVE_FAILED',
        userMessage: 'Quota exceeded',
      }
    );

    setItemSpy.mockRestore();
  });

  it('preserves non-Error profile save failures', async () => {
    mockAuthUpdateUser.mockResolvedValueOnce({
      error: 'profile service unavailable',
    });

    await expect(saveProfile({ name: 'Alice' })).rejects.toMatchObject({
      code: 'ACCOUNT_PROFILE_SAVE_FAILED',
      userMessage: 'profile service unavailable',
    });
  });
});
