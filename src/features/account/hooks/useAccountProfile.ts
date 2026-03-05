import type { FormEvent } from 'react';
import { useCallback, useMemo, useState } from 'react';
import { savePreferences, saveProfile } from '../api';
import type { AccountPreferencesPayload } from '../types';
import { toUiError } from '../../../lib/ui-error';

interface AccountUser {
  name?: string;
  email?: string;
}

export interface AccountState {
  name: string;
  email: string;
  saved: boolean;
  error: string | null;
  saving: boolean;
  preferences: AccountPreferencesPayload;
  setName: (value: string) => void;
  togglePreference: (key: keyof AccountPreferencesPayload) => void;
  handleSave: (e: FormEvent) => Promise<void>;
}

export const useAccountProfile = (user?: AccountUser | null): AccountState => {
  const [name, setName] = useState(user?.name || '');
  const email = useMemo(() => user?.email || '', [user?.email]);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [preferences, setPreferences] = useState<AccountPreferencesPayload>({
    summaries: true,
    notifications: true,
    familyMode: false,
  });

  const togglePreference = useCallback((key: keyof AccountPreferencesPayload) => {
    setPreferences(prev => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const handleSave = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      setError(null);
      setSaving(true);
      try {
        await Promise.all([saveProfile({ name }), savePreferences(preferences)]);
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      } catch (err) {
        const uiError = toUiError(err, {
          code: 'ACCOUNT_SAVE_FAILED',
          userMessage: 'We could not save your account changes.',
        });
        setError(uiError.userMessage);
      } finally {
        setSaving(false);
      }
    },
    [name, preferences]
  );

  return {
    name,
    email,
    saved,
    error,
    saving,
    preferences,
    setName,
    togglePreference,
    handleSave,
  };
};
