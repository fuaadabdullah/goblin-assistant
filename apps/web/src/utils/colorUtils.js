/**
 * Color Utilities for GoblinOS Theme System
 *
 * Generate consistent tints/shades from research-backed base colors.
 * Maintains HSL relationships for perceptually uniform variants.
 */

/**
 * Convert hex to HSL
 * @param {string} hex - Hex color code (with or without #)
 * @returns {{h: number, s: number, l: number}} HSL values
 */
function hexToHsl(hex) {
  hex = hex.replace('#', '');
  const r = parseInt(hex.substring(0, 2), 16) / 255;
  const g = parseInt(hex.substring(2, 4), 16) / 255;
  const b = parseInt(hex.substring(4, 6), 16) / 255;
  const max = Math.max(r, g, b),
    min = Math.min(r, g, b);
  let h,
    s,
    l = (max + min) / 2;
  if (max === min) {
    h = s = 0;
  } else {
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

/**
 * Convert HSL to hex
 * @param {number} h - Hue (0-360)
 * @param {number} s - Saturation (0-100)
 * @param {number} l - Lightness (0-100)
 * @returns {string} Hex color code
 */
function hslToHex(h, s, l) {
  s /= 100;
  l /= 100;
  const k = (n) => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = (n) => {
    const color = l - a * Math.max(Math.min(k(n) - 3, 9 - k(n), 1), -1);
    return Math.round(255 * color)
      .toString(16)
      .padStart(2, '0');
  };
  return `#${f(0)}${f(8)}${f(4)}`;
}

/**
 * Generate consistent color variants from a base hex
 * @param {string} hex - Base hex color
 * @returns {{base: string, light: string, dark: string, mid: string, hover: string}}
 */
export function generateVariants(hex) {
  const hsl = hexToHsl(hex);
  return {
    base: hex,
    light: hslToHex(hsl.h, hsl.s, Math.min(95, hsl.l + 20)), // +20% lighter (e.g., 300)
    dark: hslToHex(hsl.h, hsl.s, Math.max(8, hsl.l - 18)), // -18% darker (e.g., 600)
    mid: hslToHex(hsl.h, hsl.s, Math.min(80, hsl.l + 8)), // +8% mid-tone
    hover: hslToHex(hsl.h, hsl.s, Math.max(5, hsl.l - 5)) // -5% for hover state
  };
}

/**
 * Generate rgba string for glow effects
 * @param {string} hex - Base hex color
 * @param {number} alpha - Opacity (0-1)
 * @returns {string} rgba() string
 */
export function hexToRgba(hex, alpha = 1) {
  hex = hex.replace('#', '');
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * Generate complete theme palette from research-backed bases
 * @param {{primary: string, accent: string, cta: string}} baseColors
 * @returns {Object} Complete color palette with variants
 */
export function generateThemePalette(baseColors) {
  return {
    primary: generateVariants(baseColors.primary),
    accent: generateVariants(baseColors.accent),
    cta: generateVariants(baseColors.cta)
  };
}

/**
 * GoblinOS research-backed color palette
 * Base colors verified for accessibility and brand consistency
 *
 * NOTE: For theme system integration, import from '../theme/theme.js'
 * These values are kept for backwards compatibility with existing utilities.
 */
export const GOBLINOS_BASE_COLORS = {
  primary: 'var(--primary)', // Reference CSS variable
  accent: 'var(--accent)',
  cta: 'var(--cta)',
  bg: 'var(--bg)',
  surface: 'var(--surface)',
  text: 'var(--text)',
  muted: 'var(--muted)'
};

/**
 * Generate CSS custom properties from palette
 * @param {Object} palette - Color palette object
 * @returns {string} CSS custom properties string
 */
export function generateCssVariables(palette) {
  const vars = [];
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

// Generate the full GoblinOS palette
export const GOBLINOS_PALETTE = generateThemePalette(GOBLINOS_BASE_COLORS);

// Example usage (for Node.js environments)
if (typeof process !== 'undefined' && import.meta.url === `file://${process.argv[1]}`) {
  console.log('\n=== GoblinOS Color Palette ===\n');
  console.log('Primary (Goblin Green):');
  console.log('  Base:', GOBLINOS_PALETTE.primary.base);
  console.log('  Light (300):', GOBLINOS_PALETTE.primary.light);
  console.log('  Dark (600):', GOBLINOS_PALETTE.primary.dark);
  console.log('  Hover:', GOBLINOS_PALETTE.primary.hover);
  console.log('\nAccent (Magenta):');
  console.log('  Base:', GOBLINOS_PALETTE.accent.base);
  console.log('  Light (300):', GOBLINOS_PALETTE.accent.light);
  console.log('  Dark (600):', GOBLINOS_PALETTE.accent.dark);
  console.log('\nCTA (Burnt Orange):');
  console.log('  Base:', GOBLINOS_PALETTE.cta.base);
  console.log('  Light (300):', GOBLINOS_PALETTE.cta.light);
  console.log('  Dark (600):', GOBLINOS_PALETTE.cta.dark);
  console.log('\n=== CSS Variables ===\n');
  console.log(generateCssVariables(GOBLINOS_PALETTE));
}
