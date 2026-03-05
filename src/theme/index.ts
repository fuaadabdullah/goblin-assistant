// Theme system configuration and utilities

// GoblinOS Theme Presets
export const themePresets = {
  goblin: {
    // GoblinOS Dark Theme
    '--bg-primary': '#0a0a0a',
    '--bg-secondary': '#141414',
    '--bg-tertiary': '#1e1e1e',
    '--bg-elevated': '#282828',
    '--bg-hover': '#323232',
    
    '--text-primary': '#e0e0e0',
    '--text-secondary': '#a0a0a0',
    '--text-tertiary': '#707070',
    '--text-disabled': '#4a4a4a',

    '--accent-green': '#00ff88',
    '--accent-green-dim': '#00cc6a',
    '--accent-green-bright': '#00ffaa',
    '--accent-green-alpha': 'rgba(0, 255, 136, 0.1)',

    '--success': '#00ff88',
    '--success-bg': 'rgba(0, 255, 136, 0.15)',
    '--error': '#ff4444',
    '--error-bg': 'rgba(255, 68, 68, 0.15)',
    '--warning': '#ffaa00',
    '--warning-bg': 'rgba(255, 170, 0, 0.15)',
    '--info': '#00aaff',
    '--info-bg': 'rgba(0, 170, 255, 0.15)',

    '--border-subtle': '#282828',
    '--border-medium': '#3c3c3c',
    '--border-strong': '#505050',

    '--shadow-sm': '0 1px 2px rgba(0, 0, 0, 0.5)',
    '--shadow-md': '0 2px 8px rgba(0, 0, 0, 0.6)',
    '--shadow-lg': '0 4px 16px rgba(0, 0, 0, 0.7)',
    '--shadow-xl': '0 8px 32px rgba(0, 0, 0, 0.8)',

    '--glow-green': '0 0 10px rgba(0, 255, 136, 0.3)',
    '--glow-green-strong': '0 0 20px rgba(0, 255, 136, 0.5)',

    '--font-mono': "'SF Mono', 'Monaco', 'Menlo', 'Consolas', 'Courier New', monospace",
    '--font-sans': "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif",

    '--text-xs': '0.75rem',
    '--text-sm': '0.875rem',
    '--text-base': '1rem',
    '--text-lg': '1.125rem',
    '--text-xl': '1.25rem',
    '--text-2xl': '1.5rem',
    '--text-3xl': '1.875rem',

    '--leading-tight': '1.25',
    '--leading-normal': '1.5',
    '--leading-relaxed': '1.75',

    '--space-1': '0.25rem',
    '--space-2': '0.5rem',
    '--space-3': '0.75rem',
    '--space-4': '1rem',
    '--space-6': '1.5rem',
    '--space-8': '2rem',
    '--space-12': '3rem',
    '--space-16': '4rem',

    '--radius-sm': '0.25rem',
    '--radius-md': '0.5rem',
    '--radius-lg': '0.75rem',
    '--radius-xl': '1rem',

    '--transition-fast': '150ms cubic-bezier(0.4, 0, 0.2, 1)',
    '--transition-base': '250ms cubic-bezier(0.4, 0, 0.2, 1)',
    '--transition-slow': '400ms cubic-bezier(0.4, 0, 0.2, 1)',

    '--z-base': '0',
    '--z-dropdown': '1000',
    '--z-sticky': '1100',
    '--z-modal': '1200',
    '--z-toast': '1300',
    '--z-tooltip': '1400',

    // Tailwind theme variables
    '--background': '0 0% 10%',
    '--foreground': '0 0% 95%',
    '--card': '0 0% 10%',
    '--card-foreground': '0 0% 95%',
    '--popover': '0 0% 10%',
    '--popover-foreground': '0 0% 95%',
    '--primary': '142.1 76.2% 36.3%',
    '--primary-foreground': '355.7 100% 100%',
    '--secondary': '217.2 32.6% 17.5%',
    '--secondary-foreground': '217.2 32.6% 82.9%',
    '--muted': '217.2 32.6% 17.5%',
    '--muted-foreground': '215 20.2% 65.1%',
    '--accent': '217.2 32.6% 17.5%',
    '--accent-foreground': '217.2 32.6% 82.9%',
    '--destructive': '0 84.2% 60.2%',
    '--destructive-foreground': '0 0% 98%',
    '--border': '217.2 32.6% 17.5%',
    '--input': '217.2 32.6% 17.5%',
    '--ring': '142.1 76.2% 36.3%',
    '--radius': '0.5rem',
  },
  default: {
    // Default theme (fallback)
    '--bg-primary': '#ffffff',
    '--bg-secondary': '#f3f4f6',
    '--bg-tertiary': '#e5e7eb',
    '--bg-elevated': '#ffffff',
    '--bg-hover': '#f9fafb',
    
    '--text-primary': '#111827',
    '--text-secondary': '#6b7280',
    '--text-tertiary': '#9ca3af',
    '--text-disabled': '#d1d5db',

    '--accent-green': '#10b981',
    '--accent-green-dim': '#059669',
    '--accent-green-bright': '#16a34a',
    '--accent-green-alpha': 'rgba(16, 185, 129, 0.1)',

    '--success': '#10b981',
    '--success-bg': 'rgba(16, 185, 129, 0.15)',
    '--error': '#ef4444',
    '--error-bg': 'rgba(239, 68, 68, 0.15)',
    '--warning': '#f59e0b',
    '--warning-bg': 'rgba(245, 158, 11, 0.15)',
    '--info': '#3b82f6',
    '--info-bg': 'rgba(59, 130, 246, 0.15)',

    '--border-subtle': '#e5e7eb',
    '--border-medium': '#d1d5db',
    '--border-strong': '#9ca3af',

    '--shadow-sm': '0 1px 2px rgba(0, 0, 0, 0.05)',
    '--shadow-md': '0 4px 6px rgba(0, 0, 0, 0.1)',
    '--shadow-lg': '0 10px 15px rgba(0, 0, 0, 0.1)',
    '--shadow-xl': '0 20px 25px rgba(0, 0, 0, 0.1)',

    '--glow-green': '0 0 10px rgba(16, 185, 129, 0.3)',
    '--glow-green-strong': '0 0 20px rgba(16, 185, 129, 0.5)',

    '--font-mono': "'ui-monospace', SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
    '--font-sans': "'Inter', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif",

    '--text-xs': '0.75rem',
    '--text-sm': '0.875rem',
    '--text-base': '1rem',
    '--text-lg': '1.125rem',
    '--text-xl': '1.25rem',
    '--text-2xl': '1.5rem',
    '--text-3xl': '1.875rem',

    '--leading-tight': '1.25',
    '--leading-normal': '1.5',
    '--leading-relaxed': '1.75',

    '--space-1': '0.25rem',
    '--space-2': '0.5rem',
    '--space-3': '0.75rem',
    '--space-4': '1rem',
    '--space-6': '1.5rem',
    '--space-8': '2rem',
    '--space-12': '3rem',
    '--space-16': '4rem',

    '--radius-sm': '0.25rem',
    '--radius-md': '0.5rem',
    '--radius-lg': '0.75rem',
    '--radius-xl': '1rem',

    '--transition-fast': '150ms ease-in-out',
    '--transition-base': '250ms ease-in-out',
    '--transition-slow': '400ms ease-in-out',

    '--z-base': '0',
    '--z-dropdown': '1000',
    '--z-sticky': '1100',
    '--z-modal': '1200',
    '--z-toast': '1300',
    '--z-tooltip': '1400',

    // Tailwind theme variables
    '--background': '0 0% 100%',
    '--foreground': '222.2 84% 4.9%',
    '--card': '0 0% 100%',
    '--card-foreground': '222.2 84% 4.9%',
    '--popover': '0 0% 100%',
    '--popover-foreground': '222.2 84% 4.9%',
    '--primary': '221.2 83.2% 53.3%',
    '--primary-foreground': '210.9 40% 98%',
    '--secondary': '210 40% 96.1%',
    '--secondary-foreground': '222.2 84% 4.9%',
    '--muted': '210 40% 96.1%',
    '--muted-foreground': '215.4 16.3% 46.9%',
    '--accent': '210 40% 96.1%',
    '--accent-foreground': '222.2 84% 4.9%',
    '--destructive': '0 84.2% 60.2%',
    '--destructive-foreground': '0 0% 98%',
    '--border': '214.3 31.8% 91.4%',
    '--input': '214.3 31.8% 91.4%',
    '--ring': '221.2 83.2% 53.3%',
    '--radius': '0.5rem',
  },
};

// High contrast mode styles
export const highContrastStyles = {
  colors: {
    '--bg-primary': '#ffffff',
    '--bg-secondary': '#ffffff',
    '--bg-tertiary': '#ffffff',
    '--bg-elevated': '#ffffff',
    '--bg-hover': '#ffffff',
    
    '--text-primary': '#000000',
    '--text-secondary': '#000000',
    '--text-tertiary': '#000000',
    '--text-disabled': '#000000',

    '--accent-green': '#000000',
    '--accent-green-dim': '#000000',
    '--accent-green-bright': '#000000',
    '--accent-green-alpha': 'rgba(0, 0, 0, 0.1)',

    '--success': '#000000',
    '--success-bg': 'rgba(0, 0, 0, 0.15)',
    '--error': '#000000',
    '--error-bg': 'rgba(0, 0, 0, 0.15)',
    '--warning': '#000000',
    '--warning-bg': 'rgba(0, 0, 0, 0.15)',
    '--info': '#000000',
    '--info-bg': 'rgba(0, 0, 0, 0.15)',

    '--border-subtle': '#000000',
    '--border-medium': '#000000',
    '--border-strong': '#000000',

    '--shadow-sm': '0 1px 2px rgba(0, 0, 0, 1)',
    '--shadow-md': '0 2px 8px rgba(0, 0, 0, 1)',
    '--shadow-lg': '0 4px 16px rgba(0, 0, 0, 1)',
    '--shadow-xl': '0 8px 32px rgba(0, 0, 0, 1)',

    '--glow-green': '0 0 10px rgba(0, 0, 0, 1)',
    '--glow-green-strong': '0 0 20px rgba(0, 0, 0, 1)',

    '--focus': '#000000',
  },
  shadows: {
    '--focus': '0 0 0 2px #000000',
  },
};

// Theme utilities
export const applyThemePreset = (preset: keyof typeof themePresets) => {
  const theme = themePresets[preset];
  Object.entries(theme).forEach(([key, value]) => {
    document.documentElement.style.setProperty(key, value);
  });
  
  // Add theme class to document
  document.documentElement.classList.remove('theme-default', 'theme-goblin');
  document.documentElement.classList.add(`theme-${preset}`);
};

export const enableHighContrast = (enabled: boolean) => {
  if (enabled) {
    document.documentElement.classList.add('high-contrast');
    Object.entries(highContrastStyles.colors).forEach(([key, value]) => {
      document.documentElement.style.setProperty(key, value);
    });
  } else {
    document.documentElement.classList.remove('high-contrast');
    // Re-apply current theme to restore colors
    const currentTheme = localStorage.getItem('theme-preset') || 'default';
    applyThemePreset(currentTheme as keyof typeof themePresets);
  }
};

export const getHighContrastPreference = () => {
  return document.documentElement.classList.contains('high-contrast');
};

export const getCurrentTheme = () => {
  return localStorage.getItem('theme-preset') || 'default';
};

// Initialize theme system
export const initializeTheme = () => {
  // Check for saved theme preference
  const savedTheme = localStorage.getItem('theme-preset') || 'goblin';
  applyThemePreset(savedTheme as keyof typeof themePresets);
  
  // Check for high contrast preference
  const highContrast = localStorage.getItem('high-contrast') === 'true';
  enableHighContrast(highContrast);
};
