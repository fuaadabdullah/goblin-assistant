interface Hsl {
  h: number;
  s: number;
  l: number;
}

export interface ColorVariants {
  base: string;
  light: string;
  dark: string;
  mid: string;
  hover: string;
}

export interface BaseColors {
  primary: string;
  accent: string;
  cta: string;
}

export type ThemePalette = Record<string, ColorVariants | string>;

function hexToHsl(hex: string): Hsl {
  const clean = hex.replace('#', '');
  const r = parseInt(clean.substring(0, 2), 16) / 255;
  const g = parseInt(clean.substring(2, 4), 16) / 255;
  const b = parseInt(clean.substring(4, 6), 16) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r:
        h = (g - b) / d + (g < b ? 6 : 0);
        break;
      case g:
        h = (b - r) / d + 2;
        break;
      case b:
        h = (r - g) / d + 4;
        break;
    }
    h /= 6;
  }

  return { h: Math.round(h * 360), s: Math.round(s * 100), l: Math.round(l * 100) };
}

function hslToHex(h: number, s: number, l: number): string {
  const sn = s / 100;
  const ln = l / 100;
  const k = (n: number) => (n + h / 30) % 12;
  const a = sn * Math.min(ln, 1 - ln);
  const f = (n: number) => {
    const color = ln - a * Math.max(Math.min(k(n) - 3, 9 - k(n), 1), -1);
    return Math.round(255 * color).toString(16).padStart(2, '0');
  };
  return `#${f(0)}${f(8)}${f(4)}`;
}

export function generateVariants(hex: string): ColorVariants {
  const hsl = hexToHsl(hex);
  return {
    base: hex,
    light: hslToHex(hsl.h, hsl.s, Math.min(95, hsl.l + 20)),
    dark: hslToHex(hsl.h, hsl.s, Math.max(8, hsl.l - 18)),
    mid: hslToHex(hsl.h, hsl.s, Math.min(80, hsl.l + 8)),
    hover: hslToHex(hsl.h, hsl.s, Math.max(5, hsl.l - 5)),
  };
}

export function hexToRgba(hex: string, alpha = 1): string {
  const clean = hex.replace('#', '');
  const r = parseInt(clean.substring(0, 2), 16);
  const g = parseInt(clean.substring(2, 4), 16);
  const b = parseInt(clean.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function generateThemePalette(
  baseColors: BaseColors
): Record<keyof BaseColors, ColorVariants> {
  return {
    primary: generateVariants(baseColors.primary),
    accent: generateVariants(baseColors.accent),
    cta: generateVariants(baseColors.cta),
  };
}

export const GOBLINOS_BASE_COLORS = {
  primary: 'var(--primary)',
  accent: 'var(--accent)',
  cta: 'var(--cta)',
  bg: 'var(--bg)',
  surface: 'var(--surface)',
  text: 'var(--text)',
  muted: 'var(--muted)',
} as const;

export function generateCssVariables(palette: ThemePalette): string {
  const vars: string[] = [];
  Object.entries(palette).forEach(([role, variants]) => {
    if (typeof variants === 'string') {
      vars.push(`  --${role}: ${variants};`);
    } else {
      vars.push(`  --${role}: ${variants.base};`);
      if (variants.light) vars.push(`  --${role}-300: ${variants.light};`);
      if (variants.dark) vars.push(`  --${role}-600: ${variants.dark};`);
      if (variants.hover) vars.push(`  --${role}-hover: ${variants.hover};`);
    }
  });
  return `:root {\n${vars.join('\n')}\n}`;
}

export const GOBLINOS_PALETTE = generateThemePalette(GOBLINOS_BASE_COLORS);
