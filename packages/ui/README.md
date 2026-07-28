# @goblin/ui

Shared Goblin Assistant UI primitives and design tokens.

This package is the source of truth for reusable component styling. App-local
files under `apps/web/src/components/ui` remain as compatibility shims, but new
primitive styling should be authored here.

## Tokens

CSS tokens are published from:

```css
@import '@goblin/ui/tokens';
```

Token groups:

- `colors.css`: primitive palette values.
- `themes/dark.css`: default warm dark semantic theme.
- `themes/light.css`: light theme semantic overrides.
- `themes/high-contrast.css`: high-contrast semantic overrides.
- `typography.css`: font stacks, type scale, line heights, weights, tracking.
- `spacing.css`: 8px layout grid plus compatibility aliases.
- `radius.css`: radius scale capped at 8px for core UI surfaces.
- `elevation.css`: shadows, focus rings, glow aliases, z-index scale.
- `motion.css`: duration/easing tokens with reduced-motion collapse.

Components should consume semantic values such as `--surface`, `--text`,
`--primary`, `--border`, and `--space-4`, not raw primitive colors.

## Themes

Dark is the default theme. Light and high-contrast are activated by applying a
class to `document.documentElement`:

- `goblinos-light`
- `goblinos-high-contrast`

React callers can use:

```tsx
import { ThemeProvider, useTheme } from '@goblin/ui';
```

`ThemeProvider` supports localStorage persistence, a default theme, and
high-contrast preference detection.

## Components

Exported primitives:

- `Button`
- `Card`
- `Input`
- `Select`
- `Dialog`
- `Tabs`
- `Sidebar`
- `Sheet`
- `Tooltip`
- `Badge`
- `Avatar`
- `Skeleton`
- `Spinner`

Composed state helpers such as `EmptyState`, `PageState`, and
`TristateWrapper` also live here so app screens do not fork loading, empty, and
error treatments.

## Commands

```bash
pnpm --filter @goblin/ui run type-check
pnpm --filter @goblin/web run type-check
pnpm --filter @goblin/web run build-storybook
```
