export type ThemeName = 'dark' | 'light' | 'high-contrast';

export type ColorToken =
  | 'bg'
  | 'surface'
  | 'surface-hover'
  | 'surface-active'
  | 'text'
  | 'text-inverse'
  | 'text-primary'
  | 'text-secondary'
  | 'text-muted'
  | 'primary'
  | 'accent'
  | 'cta'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'border'
  | 'divider';

export type SpacingToken =
  | 'space-0'
  | 'space-1'
  | 'space-2'
  | 'space-3'
  | 'space-4'
  | 'space-5'
  | 'space-6'
  | 'space-8'
  | 'space-10'
  | 'space-12'
  | 'space-16'
  | 'space-20'
  | 'space-24'
  | 'space-32';

export type RadiusToken =
  | 'radius-none'
  | 'radius-xs'
  | 'radius-sm'
  | 'radius-md'
  | 'radius-lg'
  | 'radius-xl'
  | 'radius-2xl'
  | 'radius-full';

export type ShadowToken = 'shadow-sm' | 'shadow-md' | 'shadow-lg' | 'shadow-xl' | 'shadow-2xl';
export type TypographyToken =
  | 'text-xs'
  | 'text-sm'
  | 'text-base'
  | 'text-lg'
  | 'text-xl'
  | 'text-2xl'
  | 'text-3xl'
  | 'text-4xl'
  | 'text-5xl'
  | 'text-6xl';
export type MotionToken =
  | 'duration-fast'
  | 'duration-normal'
  | 'duration-slow'
  | 'duration-enter'
  | 'duration-exit';

export const designTokens = {
  color: {
    bg: 'var(--bg)',
    surface: 'var(--surface)',
    surfaceHover: 'var(--surface-hover)',
    surfaceActive: 'var(--surface-active)',
    text: 'var(--text)',
    textInverse: 'var(--text-inverse)',
    textPrimary: 'var(--text-primary)',
    textSecondary: 'var(--text-secondary)',
    textMuted: 'var(--text-muted)',
    primary: 'var(--primary)',
    accent: 'var(--accent)',
    cta: 'var(--cta)',
    success: 'var(--success)',
    warning: 'var(--warning)',
    danger: 'var(--danger)',
    info: 'var(--info)',
    border: 'var(--border)',
    divider: 'var(--divider)',
  },
  spacing: {
    0: 'var(--space-0)',
    1: 'var(--space-1)',
    2: 'var(--space-2)',
    3: 'var(--space-3)',
    4: 'var(--space-4)',
    5: 'var(--space-5)',
    6: 'var(--space-6)',
    8: 'var(--space-8)',
    10: 'var(--space-10)',
    12: 'var(--space-12)',
  },
  radius: {
    xs: 'var(--radius-xs)',
    sm: 'var(--radius-sm)',
    md: 'var(--radius-md)',
    lg: 'var(--radius-lg)',
    full: 'var(--radius-full)',
  },
  shadow: {
    sm: 'var(--shadow-sm)',
    md: 'var(--shadow-md)',
    lg: 'var(--shadow-lg)',
    xl: 'var(--shadow-xl)',
  },
} as const;

export type DesignTokens = typeof designTokens;
