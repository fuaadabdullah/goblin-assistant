# Frontend Docs

Implementation guides and component architecture for `apps/web` (Next.js App
Router, React 19).

Every file in this directory is listed below. If you add one, add it here too.

## Architecture & organization

- `ORGANIZATION.md`: directory layout and placement rules for frontend source.
- `COMPONENT_ARCHITECTURE_GUIDELINES.md`: component size limits, separation of
  concerns, and the refactor process.
- `STATE_MANAGEMENT_GUIDELINES.md`: when to reach for React Query versus
  Zustand, with the patterns for each.
- `SERVICES_AND_UTILS.md`: the API client, Zustand stores, and shared utility
  reference.

## Design system

- `COMPONENT_LIBRARY.md`: the fullest component catalog — all eleven components
  including the Radix-backed ones, CVA authoring pattern, and the recipe for
  adding a new component.
- `UI_COMPONENT_LIBRARY.md`: props and usage for the six core atoms, plus
  guidance on when to create a component and when to pass `className`. Overlaps
  `COMPONENT_LIBRARY.md` heavily; that one is the fuller reference and the two
  should eventually be reconciled.
- `DESIGN_TOKENS.md`: token tables for color, spacing, shadow, radius, and type.
- `THEME_SYSTEM.md`: the runtime theming mechanism — `theme.ts` API, presets,
  high-contrast and reduced-motion behavior, localStorage persistence.
- `COLOR_UTILITIES.md`: HSL variant generation and the theme-CSS build script.
- `LOGO_OPTIMIZATION.md`: Logo component props, SVG assets, theme adaptation,
  and animation behavior.

## UI patterns

- `LOADING_ERROR_STATES.md`: skeleton, error, and ARIA-live patterns for async UI.

## Auth

- `PASSKEY_FRONTEND_INTEGRATION.md`: WebAuthn register and authenticate browser
  snippets.

## Testing

- `COMPONENT_TESTS.md`: running the Playwright e2e, Storybook, and accessibility
  suites.

## Notes

- Accessibility targets, the measured contrast table, and visual-regression
  procedure live in `../ux/`.
- Superseded implementation reports and migration logs are in `../archive/`.
- Several docs in this directory still describe the pre-Next.js app — references
  to `src/App.tsx`, a Vite dev server on port 5173, or `theme.js` predate the
  current `apps/web/app/` layout.
