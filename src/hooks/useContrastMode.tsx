import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

type ContrastMode = 'standard' | 'high';

interface ContrastModeContextValue {
  mode: ContrastMode;
  toggleMode: () => void;
  setMode: (newMode: ContrastMode) => void;
}

const ContrastModeContext = createContext<ContrastModeContextValue | undefined>(undefined);

const STORAGE_KEY = 'goblin-assistant-contrast-mode';

export function ContrastModeProvider({ children }: { children: ReactNode }) {
  // SSR safety: Don't access localStorage during server-side rendering
  const [mode, setModeState] = useState<ContrastMode>('standard');
  const [isHydrated, setIsHydrated] = useState(false);

  // Hydrate from localStorage on client mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'high') {
      setModeState('high');
    }
    setIsHydrated(true);
  }, []);

  useEffect(() => {
    // Only apply after hydration to avoid SSR mismatch
    if (!isHydrated) return;

    // Apply contrast mode to document
    const root = document.documentElement;
    if (mode === 'high') {
      root.classList.add('goblinos-high-contrast');
    } else {
      root.classList.remove('goblinos-high-contrast');
    }

    // Persist to localStorage
    localStorage.setItem(STORAGE_KEY, mode);
  }, [mode, isHydrated]);

  const setMode = (newMode: ContrastMode) => {
    setModeState(newMode);
  };

  const toggleMode = () => {
    setModeState(prev => (prev === 'standard' ? 'high' : 'standard'));
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
