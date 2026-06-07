import { supabase } from '@/lib/supabase';
import { UiError } from '../../../lib/ui-error';
import type { AccountPreferencesPayload, AccountProfilePayload } from '../types';

export type { AccountPreferencesPayload, AccountProfilePayload } from '../types';

const PREFS_KEY = 'goblin-account-preferences';

export const saveProfile = async (payload: AccountProfilePayload): Promise<void> => {
  const { error } = await supabase.auth.updateUser({
    data: { name: payload.name },
  });
  if (error) {
    throw new UiError(
      {
        code: 'ACCOUNT_PROFILE_SAVE_FAILED',
        userMessage: 'We could not save your profile. Please try again.',
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
        userMessage: 'We could not save your preferences. Please try again.',
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
