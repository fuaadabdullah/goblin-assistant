/**
 * GoblinOS Theme Runtime
 * Deterministic theme manipulation utilities
 */

const THEME_STORAGE_KEY = 'goblinos-theme-preference';
const CONTRAST_STORAGE_KEY = 'goblinos-high-contrast';

/**
 * Set CSS custom properties on the document root
 * @param {Object} vars - Key-value pairs of CSS variable names (without --) and values
 * @example setThemeVars({ bg: '#071117', primary: '#06D06A' })
 */
export function setThemeVars(vars = {}) {
  const root = document.documentElement;
  Object.entries(vars).forEach(([key, value]) => {
    root.style.setProperty(`--${key}`, value);
  });
}

/**
 * Enable or disable high-contrast mode
 * @param {boolean} enable - Whether to enable high-contrast mode
 */
export function enableHighContrast(enable = true) {
  const root = document.documentElement;
  root.classList.toggle('goblinos-high-contrast', enable);

  // Persist preference
  try {
    localStorage.setItem(CONTRAST_STORAGE_KEY, JSON.stringify(enable));
  } catch (e) {
    console.warn('Failed to save contrast preference:', e);
  }
}

/**
 * Get the current high-contrast preference from storage
 * @returns {boolean} Whether high-contrast mode is enabled
 */
export function getHighContrastPreference() {
  try {
    const stored = localStorage.getItem(CONTRAST_STORAGE_KEY);
    if (stored !== null) {
      return JSON.parse(stored);
    }
  } catch (e) {
    console.warn('Failed to read contrast preference:', e);
  }

  // Default: high contrast enabled (project default)
  return true;
}

/**
 * Initialize theme system on app load
 * Restores saved preferences and applies system defaults
 */
export function initializeTheme() {
  // Restore high-contrast preference
  const highContrast = getHighContrastPreference();
  enableHighContrast(highContrast);

  // Listen for system contrast changes
  const contrastMedia = window.matchMedia('(prefers-contrast: high)');
  contrastMedia.addEventListener('change', (e) => {
    // Only auto-apply if user hasn't set a preference
    const stored = localStorage.getItem(CONTRAST_STORAGE_KEY);
    if (stored === null) {
      enableHighContrast(e.matches);
    }
  });

  // Listen for reduced motion preference
  const motionMedia = window.matchMedia('(prefers-reduced-motion: reduce)');
  const handleMotionChange = (motionEvent) => {
    document.documentElement.setAttribute('data-motion-reduced', motionEvent.matches);
  };
  handleMotionChange(motionMedia);
  motionMedia.addEventListener('change', handleMotionChange);
}

/**
 * Predefined theme presets
 */
export const THEME_PRESETS = {
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
    'glow-primary': 'rgba(6, 208, 106, 0.14)'
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
    'glow-primary': 'rgba(81, 248, 227, 0.14)'
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
    'glow-primary': 'rgba(23, 224, 193, 0.14)'
  }
};

/**
 * Apply a theme preset
 * @param {string} presetName - Name of the preset to apply
 */
export function applyThemePreset(presetName = 'default') {
  const preset = THEME_PRESETS[presetName];
  if (!preset) {
    console.warn(`Unknown theme preset: ${presetName}`);
    return;
  }

  setThemeVars(preset);

  // Save preference
  try {
    localStorage.setItem(THEME_STORAGE_KEY, presetName);
  } catch (e) {
    console.warn('Failed to save theme preference:', e);
  }
}

/**
 * Get the current theme preset name from storage
 * @returns {string} The name of the active theme preset
 */
export function getCurrentThemePreset() {
  try {
    return localStorage.getItem(THEME_STORAGE_KEY) || 'default';
  } catch (e) {
    return 'default';
  }
}
