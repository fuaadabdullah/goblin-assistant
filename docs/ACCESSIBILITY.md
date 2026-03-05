# Accessibility Guidelines - Goblin Assistant

## Overview

This document outlines the accessibility (A11Y) features and testing procedures for the Goblin Assistant application. We are committed to WCAG 2.1 Level AA compliance to ensure an inclusive experience for all users.

---

## ✅ WCAG AA Compliance Status

### Contrast Ratios (WCAG Success Criterion 1.4.3)

All color combinations meet or exceed WCAG AA requirements:

| Combination                                  | Ratio       | Requirement | Status      | Usage                         |
| -------------------------------------------- | ----------- | ----------- | ----------- | ----------------------------- |
| `--text` (#e8ecef) on `--bg` (#0a0e0f)       | **16.33:1** | 4.5:1       | ✅ **PASS** | Body text                     |
| `--muted` (#8a9ba8) on `--bg` (#0a0e0f)      | **6.77:1**  | 4.5:1       | ✅ **PASS** | Secondary text                |
| `--text` (#e8ecef) on `--surface` (#151b1e)  | **14.64:1** | 4.5:1       | ✅ **PASS** | Card/panel text               |
| `--muted` (#8a9ba8) on `--surface` (#151b1e) | **6.07:1**  | 4.5:1       | ✅ **PASS** | Card secondary text           |
| `--primary` (#00ff88) on `--bg` (#0a0e0f)    | **14.46:1** | 3.0:1       | ✅ **PASS** | Headings/buttons (large text) |
| `--danger` (#ff4757) on `--bg` (#0a0e0f)     | **5.81:1**  | 4.5:1       | ✅ **PASS** | Error messages                |
| `--warning` (#ffa502) on `--bg` (#0a0e0f)    | **9.82:1**  | 4.5:1       | ✅ **PASS** | Warning messages              |
| `--info` (#3498db) on `--bg` (#0a0e0f)       | **6.15:1**  | 4.5:1       | ✅ **PASS** | Info messages                 |

**Testing Script**: `node scripts/check-contrast.js`

---

## 🎨 High Contrast Mode

### How It Works

The application provides a high-contrast mode toggle that enhances visibility for users who need stronger visual differentiation.

**Toggle Location**: Navigation bar (top-right, next to Logout button)

### Technical Implementation

- **Standard Mode**: Default dark cyberpunk theme with goblin green (#00ff88) accents
- **High Contrast Mode**: Enhanced theme with:
  - Pure black background (#000000)
  - Pure white text (#ffffff)
  - Brighter accent colors (+10-15% luminance)
  - Stronger border contrast
  - More pronounced glow effects

**Activation**: Click the contrast mode button in the navigation bar, or add `data-contrast="high"` attribute to `<html>` element programmatically.

**Persistence**: User preference is saved to `localStorage` as `goblin-assistant-contrast-mode`.

### Testing High Contrast Mode

1. Navigate to any page in the app
2. Click the contrast mode toggle button in the navigation
3. Verify all text and UI elements have increased contrast
4. Check that preference persists after page reload
5. Test with browser DevTools color picker to verify new contrast ratios

---

## 🎬 Motion Sensitivity (prefers-reduced-motion)

### Implementation

The application respects the user's `prefers-reduced-motion` system preference:

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

**Effect**: All animations, transitions, and smooth scrolling are disabled or reduced to near-instant durations.

### Testing Motion Sensitivity

**macOS**:

1. System Settings → Accessibility → Display
2. Enable "Reduce motion"
3. Reload the app
4. Verify no smooth transitions or animations occur

**Windows**:

1. Settings → Ease of Access → Display
2. Enable "Show animations in Windows"
3. Reload the app

**Browser DevTools** (Chrome/Edge):

1. Open DevTools (F12)
2. Press Cmd+Shift+P (Mac) or Ctrl+Shift+P (Windows/Linux)
3. Type "Render" and select "Show Rendering"
4. Find "Emulate CSS media feature prefers-reduced-motion"
5. Select "prefers-reduced-motion: reduce"

---

## ⌨️ Keyboard Navigation

### Focus Indicators

All interactive elements have visible focus indicators when navigated with the keyboard:

```css
:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

button:focus-visible,
a:focus-visible,
input:focus-visible,
textarea:focus-visible,
select:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
  box-shadow: 0 0 0 4px rgba(0, 255, 136, 0.2);
}
```

### Skip Link

A "Skip to main content" link is available for keyboard and screen reader users:

- **Default state**: Hidden off-screen
- **Focused state**: Appears at top-left when tabbed to
- **Purpose**: Allows users to bypass navigation and jump directly to main content

### Testing Keyboard Navigation

1. Press `Tab` to navigate through interactive elements
2. Verify focus indicators are visible and high-contrast
3. Check tab order is logical (left-to-right, top-to-bottom)
4. Test `Shift+Tab` for reverse navigation
5. Verify `Enter` and `Space` activate buttons/links
6. Test form inputs with `Tab`, `Enter`, arrow keys

**Tab Order Checklist**:

- [ ] Skip link appears first on Tab
- [ ] Navigation links follow logical order
- [ ] Form inputs are reachable and focusable
- [ ] Buttons and CTAs have visible focus states
- [ ] Modal dialogs trap focus (if present)

---

## 🔍 Testing Tools & Procedures

### 1. Lighthouse (Chrome DevTools)

**How to Run**:

1. Open Chrome DevTools (F12)
2. Navigate to "Lighthouse" tab
3. Select "Accessibility" category (can also run Performance + Best Practices)
4. Click "Analyze page load"

**Target Score**: ≥ 90 (Accessibility)

**Common Issues to Fix**:

- Missing `alt` text on images
- Insufficient color contrast (should be none with our current tokens!)
- Missing ARIA labels on interactive elements
- Missing form labels or associations

### 2. axe DevTools (Browser Extension)

**Installation**:

- Chrome: [axe DevTools Extension](https://chrome.google.com/webstore/detail/axe-devtools-web-accessib/lhdoppojpmngadmnindnejefpokejbdd)
- Firefox: [axe DevTools Add-on](https://addons.mozilla.org/en-US/firefox/addon/axe-devtools/)

**How to Run**:

1. Install the extension
2. Open DevTools (F12)
3. Navigate to "axe DevTools" tab
4. Click "Scan All of My Page"
5. Review violations categorized by severity:
   - **Critical**: Must fix immediately
   - **Serious**: High priority
   - **Moderate**: Medium priority
   - **Minor**: Low priority

**Best Practices**:

- Fix all Critical and Serious issues before production
- Document Moderate/Minor issues and prioritize in backlog
- Re-scan after fixes to verify resolution

### 3. WebAIM Contrast Checker

**Tool URL**: <https://webaim.org/resources/contrastchecker/>

**How to Use**:

1. Navigate to the contrast checker
2. Enter foreground color (e.g., `#e8ecef` for `--text`)
3. Enter background color (e.g., `#0a0e0f` for `--bg`)
4. Verify:
   - **Normal Text**: ≥ 4.5:1 (WCAG AA)
   - **Large Text**: ≥ 3:1 (WCAG AA)

**Automated Testing**:
Run `node scripts/check-contrast.js` to verify all semantic token combinations.

### 4. Screen Reader Testing

**macOS VoiceOver**:

1. Enable: Cmd+F5 or System Settings → Accessibility → VoiceOver
2. Navigate: Control+Option+Arrow keys
3. Activate: Control+Option+Space

**Windows Narrator**:

1. Enable: Windows+Ctrl+Enter
2. Navigate: Caps Lock+Arrow keys
3. Activate: Enter or Space

**NVDA (Windows, free)**:

1. Download from [nvaccess.org](https://www.nvaccess.org/download/)
2. Navigate: Arrow keys, Tab, H (headings), L (links)
3. Activate: Enter or Space

**Testing Checklist**:

- [ ] All interactive elements announced correctly
- [ ] Form labels read aloud with inputs
- [ ] Error messages announced when validation fails
- [ ] Status updates (loading, success, error) announced via ARIA live regions
- [ ] Images have descriptive `alt` text (decorative images use `alt=""`)

---

## 📋 Development Checklist

When adding new features or components:

- [ ] **Contrast**: Verify text/background combinations meet 4.5:1 (normal) or 3:1 (large text)
- [ ] **Keyboard**: Ensure all interactive elements are keyboard-accessible (Tab, Enter, Space, arrow keys)
- [ ] **Focus Indicators**: Verify `:focus-visible` styles are visible on all interactive elements
- [ ] **ARIA**: Add ARIA labels (`aria-label`, `aria-labelledby`, `aria-describedby`) where visual labels are insufficient
- [ ] **Alt Text**: Provide descriptive `alt` text for images (use `alt=""` for decorative images)
- [ ] **Semantic HTML**: Use `<button>`, `<a>`, `<input>`, `<label>` etc. instead of styled divs with click handlers
- [ ] **Form Labels**: Associate all inputs with `<label>` elements (use `htmlFor` in JSX)
- [ ] **Live Regions**: Use ARIA live regions (`aria-live="polite"` or `aria-live="assertive"`) for dynamic content announcements
- [ ] **Motion**: Test with `prefers-reduced-motion` enabled to ensure no jarring animations
- [ ] **High Contrast**: Test in high-contrast mode to ensure visibility

---

## 🚀 Production Deployment Checklist

Before deploying to production:

- [ ] Run Lighthouse audit (target: ≥ 90 Accessibility score)
- [ ] Run axe DevTools scan (fix all Critical and Serious issues)
- [ ] Run `node scripts/check-contrast.js` (verify all tokens pass WCAG AA)
- [ ] Test keyboard navigation on all major pages (Dashboard, Chat, Search, Settings, Logs)
- [ ] Test high-contrast mode toggle (verify persistence after reload)
- [ ] Test `prefers-reduced-motion` (verify animations are disabled)
- [ ] Test with VoiceOver or NVDA (verify all content is announced correctly)
- [ ] Verify skip link is present and functional
- [ ] Check all form inputs have associated labels
- [ ] Verify all images have appropriate `alt` text

---

## 📚 Resources

### Official Guidance

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [MDN Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility)
- [A11y Project Checklist](https://www.a11yproject.com/checklist/)

### Testing Tools

- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [axe DevTools](https://www.deque.com/axe/devtools/)
- [Lighthouse (Chrome DevTools)](https://developers.google.com/web/tools/lighthouse)
- [WAVE Browser Extension](https://wave.webaim.org/extension/)

### Learning Resources

- [WebAIM Articles](https://webaim.org/articles/)
- [Inclusive Components](https://inclusive-components.design/)
- [A11y Coffee](https://a11y.coffee/)

---

## 🛠️ Scripts

### Contrast Audit

```bash
node scripts/check-contrast.js
```

Verifies all semantic token combinations meet WCAG AA contrast requirements.

**Exit Codes**:

- `0`: All tests passed
- `1`: One or more tests failed

---

## 📝 Changelog

### v1.0.0 (December 2, 2025)

- ✅ Initial WCAG AA compliance verified (all contrast ratios pass)
- ✅ High-contrast mode implemented with toggle in navigation
- ✅ `prefers-reduced-motion` support added
- ✅ Focus indicators enhanced with goblin green outline + shadow
- ✅ Skip link added for keyboard/screen reader users
- ✅ Contrast audit script created (`scripts/check-contrast.js`)

---

## 📞 Questions?

If you have questions about accessibility implementation or encounter issues, please:

1. Review this documentation first
2. Check WCAG 2.1 guidelines for authoritative guidance
3. Run automated tests (Lighthouse, axe DevTools) to identify specific issues
4. Consult the [A11y Project](https://www.a11yproject.com/) for best practices

**Remember**: Accessibility is not a one-time task—it's an ongoing commitment. Test early, test often, and consider diverse user needs in every design decision.
