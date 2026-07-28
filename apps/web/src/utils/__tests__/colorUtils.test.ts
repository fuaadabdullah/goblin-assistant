import { describe, expect, it } from 'vitest';

import {
  GOBLINOS_BASE_COLORS,
  GOBLINOS_PALETTE,
  generateCssVariables,
  generateThemePalette,
  generateVariants,
  hexToRgba,
} from '../colorUtils';

describe('colorUtils', () => {
  it('generates theme variants for vivid and neutral colors', () => {
    const vivid = generateVariants('#336699');
    const neutral = generateVariants('#000000');

    expect(vivid.base).toBe('#336699');
    expect(neutral.base).toBe('#000000');
    expect(vivid.light).toMatch(/^#[0-9a-f]{6}$/i);
    expect(vivid.dark).toMatch(/^#[0-9a-f]{6}$/i);
    expect(vivid.mid).toMatch(/^#[0-9a-f]{6}$/i);
    expect(vivid.hover).toMatch(/^#[0-9a-f]{6}$/i);
    expect(neutral.light).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it('converts hex colors to rgba strings', () => {
    expect(hexToRgba('#1a2b3c', 0.5)).toBe('rgba(26, 43, 60, 0.5)');
  });

  it('generates palettes and css variables from mixed values', () => {
    const palette = generateThemePalette({
      primary: '#112233',
      accent: '#445566',
      cta: '#778899',
    });

    const css = generateCssVariables({
      primary: palette.primary,
      accent: 'var(--accent)',
      cta: palette.cta,
    });

    expect(palette.primary.base).toBe('#112233');
    expect(palette.accent.base).toBe('#445566');
    expect(palette.cta.base).toBe('#778899');
    expect(css).toContain(':root {');
    expect(css).toContain('--primary: #112233;');
    expect(css).toContain('--primary-300:');
    expect(css).toContain('--accent: var(--accent);');
    expect(css).toContain('--cta-hover:');
  });

  it('keeps the exported goblin base colors and palette in sync', () => {
    expect(GOBLINOS_BASE_COLORS.primary).toBe('var(--primary)');
    expect(GOBLINOS_BASE_COLORS.accent).toBe('var(--accent)');
    expect(GOBLINOS_PALETTE.primary.base).toBe('var(--primary)');
  });
});
