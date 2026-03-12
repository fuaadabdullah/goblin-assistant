import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

type ThemeMode = 'dark' | 'light' | 'high';

interface ContrastModeContextValue {
  mode: ThemeMode;
  toggleMode: () => void;
  setMode: (newMode: ThemeMode) => void;
}

const ContrastModeContext = createContext<ContrastModeContextValue | undefined>(undefined);

const STORAGE_KEY = 'goblin-assistant-contrast-mode';

const MODE_CYCLE: ThemeMode[] = ['dark', 'light', 'high'];

export function ContrastModeProvider({ children }: { children: ReactNode }) {
  // SSR safety: Don't access localStorage during server-side rendering
  const [mode, setModeState] = useState<ThemeMode>('dark');
  const [isHydrated, setIsHydrated] = useState(false);

  // Hydrate from localStorage on client mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'high' || stored === 'light' || stored === 'dark') {
      setModeState(stored);
    }
    setIsHydrated(true);
  }, []);

  useEffect(() => {
    // Only apply after hydration to avoid SSR mismatch
    if (!isHydrated) return;

    // Apply theme mode to document
    const root = document.documentElement;
    root.classList.remove('goblinos-high-contrast', 'goblinos-light');
    if (mode === 'high') {
      root.classList.add('goblinos-high-contrast');
    } else if (mode === 'light') {
      root.classList.add('goblinos-light');
    }

    // Persist to localStorage
    localStorage.setItem(STORAGE_KEY, mode);
  }, [mode, isHydrated]);

  const setMode = (newMode: ThemeMode) => {
    setModeState(newMode);
  };

  const toggleMode = () => {
    setModeState(prev => {
      const idx = MODE_CYCLE.indexOf(prev);
      return MODE_CYCLE[(idx + 1) % MODE_CYCLE.length];
    });
  };

  return (
    <ContrastModeContext.Provider value={{ mode, setMode, toggleMode }}>
      {children}
    </ContrastModeContext.Provider>
  );
}

export function useContrastMode() {
  const context = useContext(ContrastModeContext);
  if (context === undefined) {
    throw new Error('useContrastMode must be used within a ContrastModeProvider');
  }
  return context;
}
