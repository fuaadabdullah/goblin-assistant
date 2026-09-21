# UX Docs

Accessibility, visual quality, and user-experience verification docs.

## Accessibility

- `ACCESSIBILITY.md`: WCAG AA targets, the measured contrast table, keyboard
  rules, and the VoiceOver/NVDA testing procedure.

## Testing

- `VISUAL_REGRESSION_TESTING.md`: writing Storybook stories and running
  Chromatic visual checks, including CI integration.
- `RESPONSIVE_TESTING.md`: viewport matrix and DevTools procedure for
  responsive checks.

## Notes

- Contrast ratios are not maintained by hand. `node tooling/quality/check-contrast.js`
  reads the live tokens from `apps/web/src/theme/index.css` and audits every
  themed block, so the numbers cannot drift from what ships.
- Component and design-system docs live in `../frontend/`.
- Superseded accessibility and visual-regression reports are in `../archive/`.
