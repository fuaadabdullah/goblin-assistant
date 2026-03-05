'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';

interface ThemeContextType {
  theme: string;
  highContrast: boolean;
  setTheme: (theme: string) => void;
  toggleHighContrast: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

interface ThemeProviderProps {
  children: React.ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const [theme, setTheme] = useState<string>('default');
  const [highContrast, setHighContrast] = useState<boolean>(false);

  useEffect(() => {
    // Initialize theme from localStorage
    const savedTheme = localStorage.getItem('theme-preset') || 'default';
    const savedHighContrast = localStorage.getItem('high-contrast') === 'true';
    
    setTheme(savedTheme);
    setHighContrast(savedHighContrast);
    
    // Apply theme
    document.documentElement.setAttribute('data-theme', savedTheme);
    if (savedHighContrast) {
      document.documentElement.classList.add('high-contrast');
    }
  }, []);

  const handleSetTheme = (newTheme: string) => {
    setTheme(newTheme);
    localStorage.setItem('theme-preset', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };

  const handleToggleHighContrast = () => {
    const newHighContrast = !highContrast;
    setHighContrast(newHighContrast);
    localStorage.setItem('high-contrast', newHighContrast.toString());
    
    if (newHighContrast) {
      document.documentElement.classList.add('high-contrast');
    } else {
      document.documentElement.classList.remove('high-contrast');
    }
  };

  return (
    <ThemeContext.Provider
      value={{
        theme,
        highContrast,
        setTheme: handleSetTheme,
        toggleHighContrast: handleToggleHighContrast,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
};
