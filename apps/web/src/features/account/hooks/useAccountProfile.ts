import type { FormEvent } from 'react';
import { useCallback, useMemo, useState } from 'react';
import { savePreferences, saveProfile, loadPreferences } from '../api';
import type { AccountPreferencesPayload } from '../types';
import { useToast } from '../../../hooks/useToast';

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

const defaultPreferences: AccountPreferencesPayload = {
  summaries: true,
  notifications: true,
  familyMode: false,
};

export const useAccountProfile = (user?: AccountUser | null): AccountState => {
  const { showSuccess } = useToast();
  const [name, setName] = useState(user?.name || '');
  const email = useMemo(() => user?.email || '', [user?.email]);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [preferences, setPreferences] = useState<AccountPreferencesPayload>(
    () => loadPreferences() ?? defaultPreferences
  );

  const togglePreference = useCallback((key: keyof AccountPreferencesPayload) => {
    setPreferences((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const handleSave = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      setError(null);
      setSaving(true);
      try {
        await Promise.all([saveProfile({ name }), savePreferences(preferences)]);
        setSaved(true);
        showSuccess('Account updated', 'Your profile and preferences were saved.');
        setTimeout(() => setSaved(false), 2000);
      } catch {
        setError('We could not save your account changes.');
      } finally {
        setSaving(false);
      }
    },
    [name, preferences, showSuccess]
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
