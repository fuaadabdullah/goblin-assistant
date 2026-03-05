/**
 * TypeScript declarations for GoblinOS Theme Runtime
 */

export interface ThemeVars {
  [key: string]: string;
}

export interface ThemePreset {
  bg: string;
  surface: string;
  text: string;
  muted: string;
  primary: string;
  'primary-600': string;
  'primary-300': string;
  accent: string;
  'accent-600': string;
  'accent-300': string;
  cta: string;
  'cta-600': string;
  'cta-300': string;
  'glow-primary': string;
  'glow-accent': string;
  'glow-cta': string;
}

export interface ThemePresets {
  default: ThemePreset;
  nocturne: ThemePreset;
  ember: ThemePreset;
}

export function setThemeVars(vars?: ThemeVars): void;
export function enableHighContrast(enable?: boolean): void;
export function getHighContrastPreference(): boolean;
export function initializeTheme(): void;
export function applyThemePreset(presetName?: keyof ThemePresets): void;
export function getCurrentThemePreset(): string;

export const THEME_PRESETS: ThemePresets;
