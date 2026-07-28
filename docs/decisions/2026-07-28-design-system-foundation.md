# Design System Foundation

**Status:** Accepted

**Date:** 2026-07-28

## Context

Goblin Assistant frontend work is moving from isolated screens toward a unified
workspace experience. The web app had reusable-looking components under
`apps/web/src/components/ui`, but those files owned their own CVA variants,
colors, focus styles, motion values, and typography choices. That made every
new screen a chance to fork the visual language.

The platform needs a single foundation that other frontend slices can consume
without reauthoring primitive styling.

## Decision

`packages/ui` is the canonical owner for shared UI tokens and primitive
components. `apps/web/src/components/ui` remains as a compatibility layer that
re-exports from `@goblin/ui`, preserving existing app imports while eliminating
duplicated primitive styling.

The package owns:

- Design token CSS under `packages/ui/src/tokens`.
- Theme switching helpers under `packages/ui/src/theme`.
- Core primitives: `Button`, `Card`, `Input`, `Select`, `Dialog`, `Tabs`,
  `Sidebar`, `Sheet`, `Tooltip`, `Badge`, `Avatar`, `Skeleton`, and `Spinner`.
- Composed loading, empty, and error state helpers.

`apps/web` imports `@goblin/ui/tokens` from `src/index.css`, scans
`../../packages/ui/src` in Tailwind content, and maps semantic token names into
Tailwind utilities.

## Consequences

- New screen work can use the app compatibility imports or import directly from
  `@goblin/ui`; either path resolves to the same implementation.
- Theme values now live next to the components that rely on them.
- Dark, light, and high-contrast themes share one semantic token contract.
- The web app keeps app-specific effects such as scanlines, glow utility
  classes, and skip links in `apps/web/src/theme/index.css`.
- Visual and a11y regression coverage should build on the Storybook foundation
  board introduced with this slice.

## Follow-Up

- Extend Tailwind token mapping as new utilities are needed.
- Replace remaining screen-level one-off visual patterns opportunistically when
  those screens are already being edited.
- Add a visual regression check for the Storybook foundation board.
