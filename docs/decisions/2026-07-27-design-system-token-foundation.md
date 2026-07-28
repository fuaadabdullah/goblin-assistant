# Design System & Token Foundation

**Status:** Accepted · 2026-07-27

**Deciders:** Frontend platform

**Related:** `packages/ui`, `apps/web`, frontend renaissance initiative

---

## Context

Goblin Assistant has accumulated visual debt across the web app:

- Color, spacing, and motion values were scattered between `apps/web/src/theme/index.css`,
  `apps/web/tailwind.config.js`, and inline component styles.
- A 4px-aligned spacing scale mixed with raw `px` values made consistent layout impossible.
- Hardcoded `duration-150`, `0.3s`, etc. bypassed any motion system — accessibility wins
  from `prefers-reduced-motion` only worked for animations that already used tokens.
- The design tokens lived in the app, not the design system package — making the
  `@goblin/ui` components implicitly depend on tokens only defined at app load.
- No theme provider, no theme persistence, no consistent dark/light/HC handling.

The frontend renaissance goal is to ship a "polished AI operating system." Every other
agent (workspace shell, chat, settings, etc.) will be built on top of a primitive
foundation. We need that foundation first, and it needs to live where components
live: in `@goblin/ui`.

## Decision

We move the design system into `packages/ui` as a single source of truth:

### 1. Token organization (`packages/ui/src/tokens/`)

```
tokens/
  colors.css        # Primitive palette (amber/coral/gold/neutral/semantic scales)
  typography.css    # Font families, type scale, weights, line heights, tracking
  spacing.css       # 8px grid (--space-0 … --space-32) + layout aliases
  elevation.css     # Shadow scale (xs…2xl), z-index scale, focus rings, glows
  radius.css        # Border radius (xs…2xl, full) + semantic aliases
  motion.css        # Durations (instant/fast/normal/slow/enter/exit), easings
  themes/
    dark.css        # Default warm amber on near-black
    light.css       # Warm beige, darker accents for AA
    high-contrast.css  # Pure black/white, brighter accents for AAA
  index.css         # Aggregates all token files + global utility classes
  tokens.ts         # TypeScript types for token names (ColorToken, etc.)
```

Importing the public entry point:

```ts
// CSS side
@import '@goblin/ui/tokens';

// React side
import { ThemeProvider, useTheme } from '@goblin/ui';
```

### 2. Token contract

- **All values are CSS custom properties**, not Tailwind-only or JS-only.
- **All components reference semantic tokens** (`--primary`, `--text`, `--surface`),
  never primitive scales (`--color-amber-400`).
- **All themes override semantic tokens only**; primitive palette stays constant.
- **Spacing is a strict 8px grid**; legacy 4px-aligned values remain as compatibility
  aliases (`--space-1`, `--space-3`, `--space-5`, `--space-7`) for one release.
- **Motion is purpose-based** (`--duration-fast`, `--duration-normal`), not numeric.

### 3. ThemeProvider

A React context provider in `packages/ui/src/theme/theme-provider.tsx`:

- Accepts `defaultTheme`, `storageKey`, and `disablePersistence` props.
- Hydrates from `localStorage` on mount; falls back to `prefers-color-scheme`.
- Auto-detects `prefers-contrast: more` for HC.
- Exposes `useTheme()` returning `{ theme, setTheme, toggleTheme, isDark, isHighContrast }`.
- Listens to `prefers-color-scheme` changes when no explicit user preference is set.

### 4. Tailwind bridge

`apps/web/tailwind.config.js` is updated to map every token into the corresponding
Tailwind theme key:

- `colors`: all semantic color tokens → Tailwind color utilities
- `fontSize`, `fontFamily`, `fontWeight`, `lineHeight`, `letterSpacing`: typography
- `spacing`: 8px grid → spacing/padding/margin/gap utilities
- `borderRadius`: radius scale
- `boxShadow`, `transitionDuration`, `transitionTimingFunction`, `zIndex`: the rest

This means existing class names like `bg-primary`, `p-4`, `shadow-md` continue to
work — they now resolve to the new tokens instead of the old ones.

### 5. Reduced motion is automatic

The `motion.css` token file contains a `prefers-reduced-motion: reduce` media query
that collapses all `--duration-*` tokens to `0.01ms`. Components don't need to do
anything extra; using a token in a Tailwind class (`duration-normal`) is sufficient
to honor the user's OS-level preference.

## Consequences

### Positive

- **Single source of truth.** Changing a token in `packages/ui/src/tokens/` propagates
  to every component in every app. No more "did I update all the places?"
- **Theme switching is trivial.** Drop a `<ThemeProvider>` in the root, and every
  component reflows.
- **Accessibility wins are free.** Contrast, focus rings, and reduced motion are
  tokenized; the next person to write a component can't accidentally bypass them.
- **Cross-app reuse.** Any future app (admin, mobile-web, embedded) can depend on
  `@goblin/ui/tokens` and get the full design system.

### Negative / Migration cost

- **Legacy 4px-aligned spacing values** are still valid (as `--space-1` … `--space-7`)
  but are documented as deprecated. Components should switch to `--space-2`, `--space-4`,
  etc. over the next refactor pass.
- **Direct references to `--bg-subtle`, `--text-muted` etc. in `apps/web/src/index.css`**
  will resolve from the new theme files. Any app-level styles that assumed the old
  `:root` color values need to be re-checked.
- **TypeScript types for token names** (`ColorToken`, etc.) are advisory — they don't
  prevent raw strings from being passed as `var(...)` arguments. Linting for that
  is a follow-up.

### Neutral

- The existing `apps/web/src/theme/theme.ts` (theme presets, HC toggle) is **kept**
  for backward compatibility. It's a different concern (named brand palettes like
  "nocturne", "ember") and doesn't conflict with the new dark/light/HC system.
- The existing `apps/web/src/hooks/useContrastMode.ts` (`ContrastModeProvider`)
  is **kept**. The new `<ThemeProvider>` is an additional, optional layer.

## What ships in this PR

- All token files (`packages/ui/src/tokens/**`)
- `ThemeProvider` + `useTheme` hook
- Updated `packages/ui/src/index.ts` (full barrel)
- Updated `apps/web/src/index.css` (consumes `@goblin/ui/tokens`)
- Updated `apps/web/tailwind.config.js` (token → utility mapping)
- `packages/ui/README.md` (token reference)
- This ADR

## What does NOT ship yet

- Storybook setup (separate slice)
- Tooltip rebuild with Radix (separate slice)
- Component-level a11y audit (separate slice)
- Codemod for legacy 4px spacing (follow-up, not blocking)
