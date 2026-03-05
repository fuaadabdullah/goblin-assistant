// lib/store/settings-store.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UserPreferences } from '../types';

interface SettingsStore {
  preferences: UserPreferences;
  apiKeys: Record<string, string>;

  actions: {
    updatePreferences: (preferences: Partial<UserPreferences>) => void;
    updateApiKey: (provider: string, key: string) => void;
    removeApiKey: (provider: string) => void;
    resetToDefaults: () => void;
  };
}

const defaultPreferences: UserPreferences = {
  theme: 'system',
  language: 'en',
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  notifications: {
    email: true,
    push: false,
    costAlerts: true,
    usageReports: true,
    errorAlerts: true,
  },
  routingStrategy: {
    type: 'balanced',
  },
  streamingEnabled: true,
};

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set, get) => ({
      preferences: defaultPreferences,
      apiKeys: {},

      actions: {
        updatePreferences: (newPreferences) => {
          set(state => ({
            preferences: { ...state.preferences, ...newPreferences },
          }));
        },

        updateApiKey: (provider, key) => {
          set(state => ({
            apiKeys: { ...state.apiKeys, [provider]: key },
          }));
        },

        removeApiKey: (provider) => {
          set(state => ({
            apiKeys: Object.fromEntries(
              Object.entries(state.apiKeys).filter(([key]) => key !== provider)
            ),
          }));
        },

        resetToDefaults: () => {
          set({
            preferences: defaultPreferences,
            apiKeys: {},
          });
        },
      },
    }),
    {
      name: 'settings-storage',
    }
  )
);
