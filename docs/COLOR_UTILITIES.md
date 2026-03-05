# Color Utilities - GoblinOS Theme System

## Overview

The GoblinOS color system uses **research-backed base colors** and programmatically generates consistent variants using HSL color mathematics. This ensures:

- ✅ Perceptually uniform color relationships
- ✅ Consistent lightness/darkness across the palette
- ✅ Easy maintenance (change base, regenerate variants)
- ✅ WCAG AA accessibility compliance

## Files

- **`src/utils/colorUtils.js`** - Core color generation utilities
- **`scripts/generate-theme-css.js`** - Build script to generate CSS variables

## Base Colors (Research-Backed)

```javascript
export const GOBLINOS_BASE_COLORS = {
  primary: '#06D06A', // Goblin green - energy, growth, tech
  accent: '#FF2AA8', // Magenta - eyes, highlights, special
  cta: '#FF6A1A', // Burnt-orange - calls-to-action
  bg: '#071117', // Deep charcoal - main background
  surface: '#0b1617', // Card/panel surface
  text: '#E6F2F1', // High-contrast text
  muted: '#9AA5A8', // Secondary text
};
```

## Usage

### 1. Generate Variants Programmatically

```javascript
import { generateVariants } from './utils/colorUtils.js';

const goblinGreen = '#06D06A';
const variants = generateVariants(goblinGreen);

console.log(variants);
// {
//   base: '#06D06A',
//   light: '#43f99e',  // +20% lightness (for 300 shades)
//   dark: '#04773d',   // -18% lightness (for 600 shades)
//   mid: '#08f780',    // +8% lightness (for mid-tones)
//   hover: '#06b75e'   // -5% lightness (for hover states)
// }
```

### 2. Generate Complete Theme Palette

```javascript
import { GOBLINOS_PALETTE } from './utils/colorUtils.js';

console.log(GOBLINOS_PALETTE.primary);
// {
//   base: '#06D06A',
//   light: '#43f99e',
//   dark: '#04773d',
//   mid: '#08f780',
//   hover: '#06b75e'
// }
```

### 3. Generate CSS Variables

```bash

# Preview CSS output
node scripts/generate-theme-css.js

# Write to file
node scripts/generate-theme-css.js --output src/generated-theme.css
```

**Output**:

```css
:root {
  --primary: #06d06a;
  --primary-300: #43f99e;
  --primary-600: #04773d;
  --primary-hover: #06b75e;

  --accent: #ff2aa8;
  --accent-300: #ff8fd0;
  --accent-600: #cc0077;
  --accent-hover: #ff0f9b;

  --cta: #ff6a1a;
  --cta-300: #ffac80;
  --cta-600: #bd4200;
  --cta-hover: #ff5900;

  --glow-primary: rgba(6, 208, 106, 0.14);
  --glow-accent: rgba(255, 42, 168, 0.14);
  --glow-cta: rgba(255, 106, 26, 0.14);
}
```

### 4. Generate RGBA for Glow Effects

```javascript
import { hexToRgba } from './utils/colorUtils.js';

const glowPrimary = hexToRgba('#06D06A', 0.14);
// 'rgba(6, 208, 106, 0.14)'

const glowAccent = hexToRgba('#FF2AA8', 0.22);
// 'rgba(255, 42, 168, 0.22)'
```

## API Reference

### `generateVariants(hex)`

Generates consistent color variants from a base hex color.

**Parameters**:

- `hex` (string) - Base hex color (with or without #)

**Returns**: Object with properties:

- `base` - Original hex color
- `light` - Lighter variant (+20% lightness)
- `dark` - Darker variant (-18% lightness)
- `mid` - Mid-tone variant (+8% lightness)
- `hover` - Hover state variant (-5% lightness)

**Example**:

```javascript
const variants = generateVariants('#06D06A');
```

### `hexToRgba(hex, alpha)`

Converts hex color to RGBA string for glow effects.

**Parameters**:

- `hex` (string) - Hex color
- `alpha` (number) - Opacity (0-1), default: 1

**Returns**: RGBA string

**Example**:

```javascript
const glow = hexToRgba('#06D06A', 0.14);
// 'rgba(6, 208, 106, 0.14)'
```

### `generateThemePalette(baseColors)`

Generates complete theme palette with variants for all base colors.

**Parameters**:

- `baseColors` (object) - Object with `primary`, `accent`, `cta` hex values

**Returns**: Object with generated variants for each color

**Example**:

```javascript
const palette = generateThemePalette({
  primary: '#06D06A',
  accent: '#FF2AA8',
  cta: '#FF6A1A',
});
```

### `generateCssVariables(palette)`

Generates CSS custom properties string from palette object.

**Parameters**:

- `palette` (object) - Color palette with variants

**Returns**: CSS string with custom properties

**Example**:

```javascript
const css = generateCssVariables(GOBLINOS_PALETTE);
```

## Color Mathematics

The utilities use **HSL (Hue, Saturation, Lightness)** color space for variant generation because:

1. **Perceptually Uniform**: Changes in lightness feel consistent across all hues
2. **Predictable**: +20% lightness always produces similar visual weight
3. **Accessible**: Easier to maintain WCAG contrast ratios
4. **Maintainable**: Change base color, variants stay harmonious

### Lightness Adjustments

- **Light (300)**: `+20%` lightness (e.g., 50% → 70%)
- **Dark (600)**: `-18%` lightness (e.g., 50% → 32%)
- **Mid**: `+8%` lightness (e.g., 50% → 58%)
- **Hover**: `-5%` lightness (e.g., 50% → 45%)

### Safety Bounds

- Minimum lightness: `8%` (prevents pure black)
- Maximum lightness: `95%` (prevents pure white)

## Runtime Theming (Optional)

For dynamic theme switching at runtime:

```javascript
import { GOBLINOS_PALETTE, hexToRgba } from './utils/colorUtils.js';

function applyTheme(palette) {
  const root = document.documentElement;

  // Apply primary variants
  root.style.setProperty('--primary', palette.primary.base);
  root.style.setProperty('--primary-300', palette.primary.light);
  root.style.setProperty('--primary-600', palette.primary.dark);
  root.style.setProperty('--primary-hover', palette.primary.hover);

  // Apply glow effects
  const glowPrimary = hexToRgba(palette.primary.base, 0.14);
  root.style.setProperty('--glow-primary', glowPrimary);
}

// Apply default GoblinOS theme
applyTheme(GOBLINOS_PALETTE);
```

## Build Integration

Add to `package.json` scripts:

```json
{
  "scripts": {
    "theme:generate": "node scripts/generate-theme-css.js --output src/generated-theme.css",
    "theme:preview": "node scripts/generate-theme-css.js",
    "prebuild": "npm run theme:generate"
  }
}
```

## Testing Color Variants

Run the test script:

```bash
# Test color utility functions
node src/utils/colorUtils.js

# Generate theme CSS
node scripts/generate-theme-css.js
```

**Expected output**:

```
=== GoblinOS Color Palette ===

Primary (Goblin Green):
  Base: #06D06A
  Light (300): #43f99e
  Dark (600): #04773d
  Hover: #06b75e

✨ All variants maintain HSL relationships for perceptual uniformity
```

## Updating Colors

To change the color scheme:

1. **Update base colors** in `src/utils/colorUtils.js`:

   ```javascript
   export const GOBLINOS_BASE_COLORS = {
     primary: '#NEW_HEX', // Update this
     accent: '#NEW_HEX', // Update this
     cta: '#NEW_HEX', // Update this
   };
   ```

2. **Regenerate variants**:

   ```bash
   node scripts/generate-theme-css.js
   ```

3. **Verify contrast ratios**:

   ```bash

   node scripts/check-contrast.js
   ```

4. **Update CSS** in `src/index.css` if needed

## Benefits

✅ **Single Source of Truth**: Change base color, all variants update
✅ **Consistent Relationships**: HSL math ensures perceptual uniformity
✅ **WCAG Compliance**: Easy to verify contrast ratios
✅ **Build-Time Generation**: No runtime overhead
✅ **Type-Safe**: Works with TypeScript (add `.d.ts` if needed)

## Best Practices

1. **Always use base colors** from `GOBLINOS_BASE_COLORS`
2. **Generate variants** with `generateVariants()` instead of manual hex
3. **Run contrast checks** after changing colors
4. **Document research** behind base color choices
5. **Version control** both utilities and generated CSS

---

**Last Updated**: December 2, 2025
**Version**: 1.0.0
**Status**: Production Ready ✅
