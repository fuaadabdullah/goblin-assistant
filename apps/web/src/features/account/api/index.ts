import { apiClient } from '@/lib/api';
import { UiError } from '../../../lib/ui-error';
import { getUserMessage } from '../../../lib/error/toast';
import type { AccountPreferencesPayload, AccountProfilePayload } from '../types';

export type { AccountPreferencesPayload, AccountProfilePayload } from '../types';

export const saveProfile = async (payload: AccountProfilePayload): Promise<void> => {
  try {
    await apiClient.saveAccountProfile(payload);
  } catch (error) {
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
    await apiClient.saveAccountPreferences(payload);
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

export const loadPreferences = async (): Promise<AccountPreferencesPayload | null> => {
  try {
    const response = await apiClient.getAccountPreferences();
    if (!response) return null;
    const record = response as Record<string, unknown>;
    const uiPreferences = (record['ui_preferences'] as Record<string, unknown> | undefined) ?? {};
    return {
      summaries: Boolean(record['summaries'] ?? uiPreferences['summaries'] ?? true),
      notifications: Boolean(
        record['notifications_enabled'] ?? uiPreferences['notifications'] ?? true
      ),
      familyMode: Boolean(record['familyMode'] ?? uiPreferences['familyMode'] ?? false),
    };
  } catch {
    return null;
  }
};
