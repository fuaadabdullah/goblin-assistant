import { authUpdateUser } from '@/lib/supabase';
import { UiError } from '../../../lib/ui-error';
import { getUserMessage } from '../../../lib/error/toast';
import type { AccountPreferencesPayload, AccountProfilePayload } from '../types';

export type { AccountPreferencesPayload, AccountProfilePayload } from '../types';

const PREFS_KEY = 'goblin-account-preferences';

export const saveProfile = async (payload: AccountProfilePayload): Promise<void> => {
  const { error } = await authUpdateUser({ data: { name: payload.name } });
  if (error) {
    throw new UiError(
      {
        code: 'ACCOUNT_PROFILE_SAVE_FAILED',
        userMessage: getUserMessage(error),
      },
      error
    );
  }
};

export const savePreferences = async (payload: AccountPreferencesPayload): Promise<void> => {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(payload));
  } catch (error) {
    throw new UiError(
      {
        code: 'ACCOUNT_PREFERENCES_SAVE_FAILED',
        userMessage: getUserMessage(error),
      },
      error
    );
  }
};

export const loadPreferences = (): AccountPreferencesPayload | null => {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    return raw ? (JSON.parse(raw) as AccountPreferencesPayload) : null;
  } catch {
    return null;
  }
};
