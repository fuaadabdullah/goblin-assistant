'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';

// Supported locales
export const locales = ['en', 'ar', 'zh'] as const;
export type Locale = (typeof locales)[number];

// Default locale
export const defaultLocale: Locale = 'en';

// RTL languages
export const rtlLocales: Locale[] = ['ar'];

// Check if a locale is RTL
export const isRtlLocale = (locale: Locale): boolean => rtlLocales.includes(locale);

// Get direction for a locale
export const getDirection = (locale: Locale): 'ltr' | 'rtl' => 
  isRtlLocale(locale) ? 'rtl' : 'ltr';

// Locale display names (in their native language)
export const localeNames: Record<Locale, string> = {
  en: 'English',
  ar: 'العربية',
  zh: '中文',
};

// Messages type (will be inferred from the JSON files)
export interface Messages {
  common: {
    loading: string;
    error: string;
    success: string;
    cancel: string;
    confirm: string;
    save: string;
    delete: string;
    edit: string;
    close: string;
    send: string;
    copy: string;
    copied: string;
    retry: string;
    back: string;
    next: string;
    previous: string;
  };
  nav: {
    home: string;
    chat: string;
    dashboard: string;
    documentation: string;
    api: string;
    settings: string;
    login: string;
    logout: string;
  };
  home: {
    title: string;
    subtitle: string;
    heroTitle: string;
    heroTitleHighlight: string;
    heroDescription: string;
    getStarted: string;
    startBuilding: string;
    viewDashboard: string;
    viewLiveDemo: string;
    getStartedFree: string;
    badge: string;
    stats: {
      privacyFirst: string;
      multiProvider: string;
      smartRouting: string;
    };
    features: {
      intelligentRouting: { title: string; description: string };
      privacyFirst: { title: string; description: string };
      multiProvider: { title: string; description: string };
      developerFocused: { title: string; description: string };
    };
    useCases: {
      title: string;
      subtitle: string;
      codeAssistance: { title: string; description: string };
      dataAnalysis: { title: string; description: string };
      research: { title: string; description: string };
    };
    cta: {
      title: string;
      description: string;
    };
  };
  chat: {
    welcome: string;
    placeholder: string;
    sendMessage: string;
    clearChat: string;
    newChat: string;
    restoredConversation: string;
    newConversation: string;
    copyMessage: string;
    regenerate: string;
    scrollToBottom: string;
    thinking: string;
    errors: {
      tooLong: string;
      auth: string;
      forbidden: string;
      rateLimit: string;
      server: string;
      network: string;
      timeout: string;
      parse: string;
      generic: string;
    };
    shortcuts: {
      title: string;
      focusInput: string;
      clearChat: string;
      escape: string;
    };
  };
  settings: {
    title: string;
    language: string;
    theme: string;
    themes: {
      light: string;
      dark: string;
      system: string;
    };
  };
  language: {
    en: string;
    ar: string;
    zh: string;
  };
}

// Context type
interface I18nContextType {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
  messages: Messages | null;
  isRtl: boolean;
  direction: 'ltr' | 'rtl';
  isLoading: boolean;
}

// Create context
const I18nContext = createContext<I18nContextType | undefined>(undefined);

// Storage key for locale preference
const LOCALE_STORAGE_KEY = 'goblin_locale';

// Get nested value from object by dot-notation key
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const getNestedValue = (obj: any, path: string): string | undefined => {
  const result = path.split('.').reduce((acc: unknown, part: string) => {
    if (acc && typeof acc === 'object' && part in (acc as Record<string, unknown>)) {
      return (acc as Record<string, unknown>)[part];
    }
    return undefined;
  }, obj);
  return typeof result === 'string' ? result : undefined;
};

// Provider component
export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(defaultLocale);
  const [messages, setMessages] = useState<Messages | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load messages for a locale
  const loadMessages = useCallback(async (loc: Locale) => {
    setIsLoading(true);
    try {
      const msgs = await import(`../../messages/${loc}.json`);
      setMessages(msgs.default);
    } catch (error) {
      console.error(`Failed to load messages for locale ${loc}:`, error);
      // Fallback to English
      if (loc !== 'en') {
        const fallback = await import('../../messages/en.json');
        setMessages(fallback.default);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initialize locale from storage or browser
  useEffect(() => {
    const initLocale = () => {
      // First check localStorage
      const stored = localStorage.getItem(LOCALE_STORAGE_KEY);
      if (stored && locales.includes(stored as Locale)) {
        return stored as Locale;
      }

      // Then check browser language
      const browserLang = navigator.language.split('-')[0];
      if (locales.includes(browserLang as Locale)) {
        return browserLang as Locale;
      }

      return defaultLocale;
    };

    const initialLocale = initLocale();
    setLocaleState(initialLocale);
    loadMessages(initialLocale);
  }, [loadMessages]);

  // Update HTML attributes when locale changes
  useEffect(() => {
    if (typeof document !== 'undefined') {
      const dir = getDirection(locale);
      document.documentElement.lang = locale;
      document.documentElement.dir = dir;
      
      // Add RTL-specific class for styling
      if (dir === 'rtl') {
        document.documentElement.classList.add('rtl');
      } else {
        document.documentElement.classList.remove('rtl');
      }
    }
  }, [locale]);

  // Set locale and persist to storage
  const setLocale = useCallback((newLocale: Locale) => {
    if (locales.includes(newLocale)) {
      localStorage.setItem(LOCALE_STORAGE_KEY, newLocale);
      setLocaleState(newLocale);
      loadMessages(newLocale);
    }
  }, [loadMessages]);

  // Translation function
  const t = useCallback((key: string, params?: Record<string, string | number>): string => {
    if (!messages) return key;

    let value = getNestedValue(messages, key);
    
    if (value === undefined) {
      console.warn(`Missing translation for key: ${key}`);
      return key;
    }

    // Replace parameters like {name} with actual values
    if (params) {
      Object.entries(params).forEach(([paramKey, paramValue]) => {
        value = value?.replace(new RegExp(`\\{${paramKey}\\}`, 'g'), String(paramValue));
      });
    }

    return value || key;
  }, [messages]);

  const contextValue: I18nContextType = {
    locale,
    setLocale,
    t,
    messages,
    isRtl: isRtlLocale(locale),
    direction: getDirection(locale),
    isLoading,
  };

  return (
    <I18nContext.Provider value={contextValue}>
      {children}
    </I18nContext.Provider>
  );
}

// Hook to use i18n
export function useI18n() {
  const context = useContext(I18nContext);
  if (context === undefined) {
    throw new Error('useI18n must be used within an I18nProvider');
  }
  return context;
}

// Hook to get just the translation function
export function useTranslation() {
  const { t, locale, isRtl, direction } = useI18n();
  return { t, locale, isRtl, direction };
}
