# Viewport Testing Checklist

Manual testing checklist for mobile and tablet viewports. Run this after any
layout or CSS change, and before any release.

## Prerequisites

- Frontend running: `make web-dev`
- Backend running: `make api-dev` (or `make api-docker-up`)
- Chrome DevTools device toolbar, or physical devices

## Test Devices

| Device | Viewport | Device Pixel Ratio |
|--------|----------|-------------------|
| iPhone SE | 375 x 667 | 2x |
| iPhone 14 Pro | 393 x 852 | 3x |
| iPad Mini | 768 x 1024 | 2x |
| iPad Pro 11" | 834 x 1194 | 2x |
| Desktop (reference) | 1280 x 800 | 1x |

## Checklist

### Layout

- [ ] **Viewport meta tag** — page renders at device width, no horizontal
  scroll on any screen size
- [ ] **Header/nav** — collapses or stacks correctly on mobile; no overflow
- [ ] **Sidebar** — collapses to hamburger menu or off-canvas on mobile/tablet
- [ ] **Main content area** — fills available width without horizontal scroll
- [ ] **Footer** — stacks correctly, no overlap with content

### Chat Interface

- [ ] **Message bubbles** — wrap correctly at narrow widths; no text overflow
- [ ] **Input area** — stays above the on-screen keyboard on mobile
- [ ] **Code blocks** — horizontal scroll within code blocks (not the page)
- [ ] **Model selector** — dropdown doesn't overflow the viewport
- [ ] **Send button** — accessible without zooming

### Auth Pages

- [ ] **Login form** — inputs are full-width, no clipping
- [ ] **Register form** — same as login
- [ ] **OAuth buttons** — stack vertically on mobile, don't overflow

### Settings Pages

- [ ] **Settings sidebar** — collapses to tabs or accordion on mobile
- [ ] **Form inputs** — labels don't truncate; inputs are touch-friendly
  (min 44px tap targets)
- [ ] **Toggle switches** — large enough to tap accurately

### Typography

- [ ] **Font sizes** — body text is at least 16px on mobile (prevents
  iOS auto-zoom on input focus)
- [ ] **Line length** — max ~75 characters per line on all viewports
- [ ] **Headings** — scale proportionally on smaller screens

### Touch Targets

- [ ] **Buttons** — minimum 44x44px tap area
- [ ] **Links** — adequate spacing between adjacent links
- [ ] **Dropdowns** — items are easy to tap without precision

### Orientation

- [ ] **Portrait to landscape** — layout adapts without breaking
- [ ] **Landscape on phone** — content doesn't get cut off

## Known Issues

_ log layout breaks here as they are found. Include device, viewport, and a
  screenshot or description._

| Date | Device | Viewport | Issue | Severity | Status |
|------|--------|----------|-------|----------|--------|
| (example) | iPhone SE | 375x667 | Chat input hidden behind keyboard | High | Open |

## How to Log a Break

1. Open the page on the target device/viewport
2. Take a screenshot or note the exact behavior
3. Add a row to the Known Issues table above
4. Include: date, device, viewport size, issue description, severity
   (High = blocks usage, Medium = degraded UX, Low = cosmetic)