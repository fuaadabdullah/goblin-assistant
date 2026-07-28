import * as React from 'react';
import { cn } from '../utils';

export type ThemeName = 'dark' | 'light' | 'high-contrast';

export interface ThemeContextValue {
  theme: ThemeName;
  setTheme: (theme: ThemeName) => void;
  toggleTheme: () => void;
  isDark: boolean;
  isHighContrast: boolean;
}

export interface ThemeProviderProps {
  children: React.ReactNode;
  defaultTheme?: ThemeName;
  storageKey?: string;
  disablePersistence?: boolean;
}

const ThemeContext = React.createContext<ThemeContextValue | undefined>(undefined);

function getPreferredTheme(defaultTheme: ThemeName): ThemeName {
  if (typeof window === 'undefined') {
    return defaultTheme;
  }

  if (window.matchMedia?.('(prefers-contrast: more)').matches) {
    return 'high-contrast';
  }

  if (window.matchMedia?.('(prefers-color-scheme: light)').matches) {
    return 'light';
  }

  return defaultTheme;
}

function getStoredTheme(storageKey: string): ThemeName | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const value = window.localStorage.getItem(storageKey);
  return value === 'dark' || value === 'light' || value === 'high-contrast' ? value : null;
}

function applyThemeClass(theme: ThemeName) {
  if (typeof document === 'undefined') {
    return;
  }

  const root = document.documentElement;
  root.classList.remove('goblinos-light', 'goblinos-high-contrast');
  root.dataset['theme'] = theme;

  if (theme === 'light') {
    root.classList.add('goblinos-light');
  }

  if (theme === 'high-contrast') {
    root.classList.add('goblinos-high-contrast');
  }
}

export function ThemeProvider({
  children,
  defaultTheme = 'dark',
  storageKey = 'goblinos-theme',
  disablePersistence = false,
}: ThemeProviderProps) {
  const [theme, setThemeState] = React.useState<ThemeName>(defaultTheme);

  React.useEffect(() => {
    const initialTheme =
      !disablePersistence && getStoredTheme(storageKey)
        ? getStoredTheme(storageKey)
        : getPreferredTheme(defaultTheme);

    if (initialTheme) {
      setThemeState(initialTheme);
      applyThemeClass(initialTheme);
    }
  }, [defaultTheme, disablePersistence, storageKey]);

  const setTheme = React.useCallback(
    (nextTheme: ThemeName) => {
      setThemeState(nextTheme);
      applyThemeClass(nextTheme);

      if (!disablePersistence && typeof window !== 'undefined') {
        window.localStorage.setItem(storageKey, nextTheme);
      }
    },
    [disablePersistence, storageKey]
  );

  const toggleTheme = React.useCallback(() => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  }, [setTheme, theme]);

  const value = React.useMemo<ThemeContextValue>(
    () => ({
      theme,
      setTheme,
      toggleTheme,
      isDark: theme === 'dark',
      isHighContrast: theme === 'high-contrast',
    }),
    [setTheme, theme, toggleTheme]
  );

  return React.createElement(ThemeContext.Provider, { value }, children);
}

export function useTheme() {
  const context = React.useContext(ThemeContext);

  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }

  return context;
}

export { cn };
