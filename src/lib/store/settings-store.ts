import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { apiClient, apiEndpoints } from '../services/api-client';

export interface UserPreferences {
  theme: 'default' | 'nocturne' | 'ember';
  highContrast: boolean;
  fontSize: 'sm' | 'md' | 'lg';
  language: string;
  notifications: boolean;
  autoSave: boolean;
  compactMode: boolean;
}

export interface ProviderSettings {
  openai: {
    apiKey: string;
    model: string;
    temperature: number;
    maxTokens: number;
  };
  anthropic: {
    apiKey: string;
    model: string;
    temperature: number;
    maxTokens: number;
  };
  google: {
    apiKey: string;
    model: string;
    temperature: number;
    maxTokens: number;
  };
}

interface SettingsState {
  preferences: UserPreferences;
  providerSettings: ProviderSettings;
  isLoading: boolean;
  error: string | null;

  // Actions
  updatePreferences: (updates: Partial<UserPreferences>) => Promise<void>;
  updateProviderSettings: (provider: keyof ProviderSettings, settings: Partial<ProviderSettings[keyof ProviderSettings]>) => Promise<void>;
  loadSettings: () => Promise<void>;
  resetSettings: () => void;
  clearError: () => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      preferences: {
        theme: 'default',
        highContrast: false,
        fontSize: 'md',
        language: 'en',
        notifications: true,
        autoSave: true,
        compactMode: false,
      },
      providerSettings: {
        openai: {
          apiKey: '',
          model: 'gpt-4',
          temperature: 0.7,
          maxTokens: 4000,
        },
        anthropic: {
          apiKey: '',
          model: 'claude-3-sonnet-20240229',
          temperature: 0.7,
          maxTokens: 4000,
        },
        google: {
          apiKey: '',
          model: 'gemini-pro',
          temperature: 0.7,
          maxTokens: 4000,
        },
      },
      isLoading: false,
      error: null,

      updatePreferences: async (updates: Partial<UserPreferences>) => {
        set({ isLoading: true, error: null });
        
        try {
          const currentPreferences = get().preferences;
          const newPreferences = { ...currentPreferences, ...updates };
          
          await apiClient.put(apiEndpoints.settings.preferences, newPreferences);
          
          set({
            preferences: newPreferences,
            isLoading: false,
            error: null,
          });
        } catch (error: any) {
          const errorMessage = error.response?.data?.message || 'Failed to update preferences';
          set({
            isLoading: false,
            error: errorMessage,
          });
          throw error;
        }
      },

      updateProviderSettings: async (provider: keyof ProviderSettings, settings: Partial<ProviderSettings[keyof ProviderSettings]>) => {
        set({ isLoading: true, error: null });
        
        try {
          const currentSettings = get().providerSettings;
          const newProviderSettings = { ...currentSettings[provider], ...settings };
          const newSettings = { ...currentSettings, [provider]: newProviderSettings };
          
          await apiClient.put(`${apiEndpoints.settings.settings}/${provider}`, { settings: newProviderSettings });
          
          set({
            providerSettings: newSettings,
            isLoading: false,
            error: null,
          });
        } catch (error: any) {
          const errorMessage = error.response?.data?.message || 'Failed to update provider settings';
          set({
            isLoading: false,
            error: errorMessage,
          });
          throw error;
        }
      },

      loadSettings: async () => {
        set({ isLoading: true, error: null });
        
        try {
          const [preferences, providerSettings] = await Promise.all([
            apiClient.get<UserPreferences>(apiEndpoints.settings.preferences),
            apiClient.get<ProviderSettings>(`${apiEndpoints.settings.settings}/all`),
          ]);
          
          set({
            preferences,
            providerSettings,
            isLoading: false,
            error: null,
          });
        } catch (error: any) {
          const errorMessage = error.response?.data?.message || 'Failed to load settings';
          set({
            isLoading: false,
            error: errorMessage,
          });
          
          // Use defaults if loading fails
          set({
            preferences: get().preferences,
            providerSettings: get().providerSettings,
          });
        }
      },

      resetSettings: () => {
        set({
          preferences: {
            theme: 'default',
            highContrast: false,
            fontSize: 'md',
            language: 'en',
            notifications: true,
            autoSave: true,
            compactMode: false,
          },
          providerSettings: {
            openai: {
              apiKey: '',
              model: 'gpt-4',
              temperature: 0.7,
              maxTokens: 4000,
            },
            anthropic: {
              apiKey: '',
              model: 'claude-3-sonnet-20240229',
              temperature: 0.7,
              maxTokens: 4000,
            },
            google: {
              apiKey: '',
              model: 'gemini-pro',
              temperature: 0.7,
              maxTokens: 4000,
            },
          },
          isLoading: false,
          error: null,
        });
      },

      clearError: () => {
        set({ error: null });
      },
    }),
    {
      name: 'settings-storage',
      partialize: (state) => ({
        preferences: state.preferences,
        providerSettings: state.providerSettings,
      }),
    }
  )
);
