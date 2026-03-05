import { apiClient } from '../../../api/apiClient';
import { UiError } from '../../../lib/ui-error';
import type { AccountPreferencesPayload, AccountProfilePayload } from '../types';

export type { AccountPreferencesPayload, AccountProfilePayload } from '../types';

export const saveProfile = async (_payload: AccountProfilePayload): Promise<void> => {
  try {
    await apiClient.saveAccountProfile(_payload);
  } catch (error) {
    throw new UiError(
      {
        code: 'ACCOUNT_PROFILE_SAVE_FAILED',
        userMessage: 'We could not save your profile. Please try again.',
      },
      error
    );
  }
};

export const savePreferences = async (_payload: AccountPreferencesPayload): Promise<void> => {
  try {
    await apiClient.saveAccountPreferences(_payload);
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
