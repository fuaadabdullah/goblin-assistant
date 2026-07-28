---
title: "RESPONSIVE TESTING"
description: "Responsive Design Testing Guide"
---

# Responsive Design Testing Guide

## Quick Viewport Testing

Test the dashboard at these common viewport widths to ensure proper responsive behavior:

### Viewports to Test

| Width  | Device Type            | Expected Layout  |
| ------ | ---------------------- | ---------------- |
| 375px  | Mobile (iPhone SE)     | 1 column stacked |
| 768px  | Tablet (iPad Portrait) | 2 columns        |
| 1024px | Small Desktop          | 3 columns        |
| 1280px | Desktop                | 3-4 columns      |
| 1440px | Wide Desktop           | 4 columns        |

## Chrome DevTools Testing

### Method 1: Responsive Device Mode

1. Open Chrome DevTools (`Cmd+Option+I` on Mac, `F12` on Windows)
2. Click the device toolbar icon (`Cmd+Shift+M` or `Ctrl+Shift+M`)
3. Select "Responsive" from the device dropdown
4. Manually test each width:
   - 375px
   - 768px
   - 1024px
   - 1280px
   - 1440px

### Method 2: Device Presets

Test with these device presets:

- **iPhone SE** (375x667)
- **iPad** (768x1024)
- **iPad Pro** (1024x1366)
- **Desktop** (1280x720)
- **Large Desktop** (1440x900)

## What to Check

### Layout Breakpoints

- [ ] Cards stack properly on mobile (1 column)
- [ ] Grid transitions smoothly to 2 columns at 768px
- [ ] Grid expands to 3 columns at 1024px
- [ ] Grid maxes out at 4 columns for 1440px+
- [ ] No horizontal scrolling at any viewport
- [ ] Gap spacing remains consistent (1rem)

### Component Behavior

- [ ] StatusCard meta grid adapts (grid-cols-2 sm:grid-cols-3)
- [ ] Navigation wraps gracefully on mobile
- [ ] Header flex layout stacks on mobile (flex-col sm:flex-row)
- [ ] Quick actions buttons remain readable
- [ ] Cost stat cards don't overflow
- [ ] Touch targets are at least 44x44px

### Typography

- [ ] No text overflow or truncation
- [ ] Font sizes remain readable on mobile (min 14px body, 16px input)
- [ ] Line heights prevent cramping
- [ ] Headings scale appropriately

### Accessibility

- [ ] Focus indicators visible at all sizes
- [ ] Skip link accessible on mobile
- [ ] Aria-live regions work correctly
- [ ] Keyboard navigation functional

## Known Breakpoints Fixed

The `.grid-auto-fit` utility now includes optimized breakpoints:

- **375px**: Force 1 column on mobile
- **768px**: 2 columns with 320px minimum card width
- **1024px**: 3 columns with 300px cards
- **1280px**: 3-4 columns with 320px cards
- **1440px**: 4 columns with 340px cards

## Testing Commands

### Start Dev Server

```bash
cd apps/goblin-assistant
npm run dev
```

### Run Accessibility Tests

```bash

# Install puppeteer if needed
npm install -D puppeteer

# Run axe smoke test
node ../../tools/axe-smoke.js
```

### Check for Responsive Issues

```bash
# Lint CSS for overflow issues
npm run lint

# Check bundle size (affects mobile perf)
npm run build
```

## Common Issues to Fix

### If cards overflow:

- Check min-width in `.grid-auto-fit` (should be ≤ viewport - padding)
- Verify no fixed widths on child elements
- Ensure images/icons have max-width: 100%

### If text is unreadable:

- Increase base font size (currently 16px)
- Adjust heading scale (h1: 32px, h2: 24px, h3: 18px)
- Check contrast ratios (use axe-core)

### If touch targets are too small:

- Ensure buttons/links have min-height: 44px
- Add padding to increase clickable area
- Use larger tap targets on mobile (48x48px ideal)

## Browser Testing Matrix

| Browser        | Versions | Priority |
| -------------- | -------- | -------- |
| Chrome         | Latest 2 | High     |
| Safari (iOS)   | Latest 2 | High     |
| Firefox        | Latest 2 | Medium   |
| Edge           | Latest 2 | Medium   |
| Safari (macOS) | Latest 2 | Low      |

## Performance Targets

| Metric | Mobile  | Desktop |
| ------ | ------- | ------- |
| LCP    | < 2.5s  | < 2.0s  |
| FID    | < 100ms | < 100ms |
| CLS    | < 0.1   | < 0.1   |
| TTI    | < 3.8s  | < 3.0s  |

## Next Steps

1. ✅ Enhanced responsive grid breakpoints
2. ✅ Added loading skeletons
3. ✅ Improved error states with retry
4. ✅ Added aria-live for status updates
5. ⏳ Run manual viewport tests
6. ⏳ Run axe accessibility audit
7. ⏳ Fix contrast violations
8. ⏳ Test on real devices

## Automated Testing

Consider adding Playwright tests for viewport testing:

```typescript

// Example test
test('dashboard responsive on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto('<http://localhost:5173/dashboard');>

  // Check single column layout
  const cards = await page.locator('.grid-auto-fit > *').count();
  const firstCard = page.locator('.grid-auto-fit > *').first();
  const width = await firstCard.boundingBox();

  expect(width?.width).toBeGreaterThan(300); // Should be full width
});
```
