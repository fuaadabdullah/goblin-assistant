const THEME_STORAGE_KEY = 'goblinos-theme-preference';
const CONTRAST_STORAGE_KEY = 'goblinos-high-contrast';

const canUseDom = () =>
  typeof window !== 'undefined' &&
  typeof document !== 'undefined' &&
  typeof localStorage !== 'undefined';

export function setThemeVars(vars: Record<string, string> = {}): void {
  if (!canUseDom()) return;
  const root = document.documentElement;
  Object.entries(vars).forEach(([key, value]) => {
    root.style.setProperty(`--${key}`, value);
  });
}

export function enableHighContrast(enable = true): void {
  if (!canUseDom()) return;
  const root = document.documentElement;
  root.classList.toggle('goblinos-high-contrast', enable);

  try {
    localStorage.setItem(CONTRAST_STORAGE_KEY, JSON.stringify(enable));
  } catch {
    // Non-critical: storage may be unavailable.
  }
}

export function getHighContrastPreference(): boolean {
  if (!canUseDom()) {
    return true;
  }
  try {
    const stored = localStorage.getItem(CONTRAST_STORAGE_KEY);
    if (stored !== null) {
      return JSON.parse(stored) as boolean;
    }
  } catch {
    // Fall through to default.
  }

  return true;
}

export function initializeTheme(): void {
  if (!canUseDom()) return;
  const highContrast = getHighContrastPreference();
  enableHighContrast(highContrast);

  const contrastMedia = window.matchMedia('(prefers-contrast: high)');
  contrastMedia.addEventListener('change', (e) => {
    const stored = localStorage.getItem(CONTRAST_STORAGE_KEY);
    if (stored === null) {
      enableHighContrast(e.matches);
    }
  });

  const motionMedia = window.matchMedia('(prefers-reduced-motion: reduce)');
  const handleMotionChange = (motionEvent: MediaQueryListEvent | MediaQueryList) => {
    document.documentElement.setAttribute(
      'data-motion-reduced',
      String(motionEvent.matches)
    );
  };
  handleMotionChange(motionMedia);
  motionMedia.addEventListener('change', handleMotionChange);
}

export type ThemePresetName = 'default' | 'nocturne' | 'ember';
export type ThemePreset = Record<string, string>;

export const THEME_PRESETS: Record<ThemePresetName, ThemePreset> = {
  default: {
    bg: '#071117',
    surface: '#0b1617',
    text: '#E6F2F1',
    muted: '#9AA5A8',
    primary: '#06D06A',
    'primary-600': '#05b55a',
    'primary-300': '#59e89a',
    accent: '#FF2AA8',
    cta: '#FF6A1A',
    'glow-primary': 'rgba(6, 208, 106, 0.14)',
  },
  nocturne: {
    bg: '#05090F',
    surface: '#0c101a',
    text: '#F0F5FF',
    muted: '#8C9DB8',
    primary: '#51F8E3',
    'primary-600': '#3ed9c8',
    'primary-300': '#7ffbec',
    accent: '#C964FF',
    cta: '#FF8C32',
    'glow-primary': 'rgba(81, 248, 227, 0.14)',
  },
  ember: {
    bg: '#0A0B10',
    surface: '#141824',
    text: '#F7EFE1',
    muted: '#B4A79A',
    primary: '#17E0C1',
    'primary-600': '#13c4a9',
    'primary-300': '#4fe9d0',
    accent: '#FF4DA6',
    cta: '#FFB347',
    'glow-primary': 'rgba(23, 224, 193, 0.14)',
  },
};

export function applyThemePreset(presetName: string = 'default'): void {
  if (!canUseDom()) return;
  const preset = THEME_PRESETS[presetName as ThemePresetName];
  if (!preset) {
    return;
  }

  setThemeVars(preset);

  try {
    localStorage.setItem(THEME_STORAGE_KEY, presetName);
  } catch {
    // Non-critical: storage may be unavailable.
  }
}

export function getCurrentThemePreset(): string {
  if (!canUseDom()) {
    return 'default';
  }
  try {
    return localStorage.getItem(THEME_STORAGE_KEY) ?? 'default';
  } catch {
    return 'default';
  }
}
