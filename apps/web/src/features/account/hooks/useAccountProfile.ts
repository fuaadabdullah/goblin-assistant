import type { FormEvent } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { savePreferences, saveProfile, loadPreferences } from '../api';
import type { AccountPreferencesPayload } from '../types';
import { toUiError } from '../../../lib/ui-error';
import { useToast } from '../../../hooks/useToast';

interface AccountUser {
  name?: string | undefined;
  email?: string | undefined;
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
  const [preferences, setPreferences] = useState<AccountPreferencesPayload>(defaultPreferences);

  useEffect(() => {
    setName(user?.name || '');
  }, [user?.name]);

  useEffect(() => {
    let cancelled = false;
    loadPreferences().then((stored) => {
      if (cancelled || !stored) return;
      setPreferences(stored);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const togglePreference = (key: keyof AccountPreferencesPayload) => {
    setPreferences((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await Promise.all([saveProfile({ name }), savePreferences(preferences)]);
      setSaved(true);
      showSuccess('Account updated', 'Your profile and preferences were saved.');
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
  };

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
