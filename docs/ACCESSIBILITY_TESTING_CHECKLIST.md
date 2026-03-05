# Accessibility Testing Checklist

**Date**: December 2, 2025
**Version**: v1.0.0
**Status**: Ready for Testing

---

## ✅ Automated Testing (Completed)

### Contrast Audit ✅

- [x] Run `node scripts/check-contrast.js`
- [x] All 8 token combinations pass WCAG AA
- [x] Body text: 16.33:1 (need 4.5:1) ✅
- [x] Secondary text: 6.77:1 (need 4.5:1) ✅
- [x] All semantic colors pass ✅

---

## 🧪 Manual Testing (In Progress)

### 1. High-Contrast Mode Toggle

**Location**: Navigation bar (top-right, before Logout button)

**Test Steps**:

- [ ] Navigate to <http://localhost:3000>
- [ ] Locate contrast toggle button in navigation
- [ ] Click toggle - verify switch from Standard to High Contrast
- [ ] Check `localStorage` in DevTools - verify `goblin-assistant-contrast-mode` = `"high"`
- [ ] Reload page - verify high-contrast mode persists
- [ ] Click toggle again - verify switch back to Standard
- [ ] Test on all pages:
  - [ ] Dashboard (/)
  - [ ] Chat (/chat)
  - [ ] Search (/search)
  - [ ] Settings (/settings)
  - [ ] Providers (/providers)
  - [ ] Logs (/logs)
  - [ ] Sandbox (/sandbox)

**Expected Behavior**:

- Background changes from #0a0e0f → #000000 (pure black)
- Text changes from #e8ecef → #ffffff (pure white)
- Goblin green changes from #00ff88 → #00ffaa (brighter)
- All UI elements have increased contrast
- Toggle button icon changes (eye → lightbulb)
- Preference persists across page reloads

---

### 2. Keyboard Navigation

**Test Steps**:

- [ ] Navigate to <http://localhost:3000>
- [ ] Press Tab - verify skip link appears at top-left
- [ ] Press Enter on skip link - verify jump to main content
- [ ] Press Tab repeatedly through navigation links
- [ ] Verify each element shows:
  - [ ] 2px solid goblin green outline
  - [ ] 2px outline offset (space between element and outline)
  - [ ] Subtle glow effect (rgba(0, 255, 136, 0.2))
- [ ] Check tab order is logical (left-to-right, top-to-bottom)
- [ ] Test Shift+Tab for reverse navigation

**Pages to Test**:

- [ ] Dashboard - Quick action buttons
- [ ] Chat - Message input, send button
- [ ] Search - Search input, search button
- [ ] Settings - All form inputs and selects
- [ ] Providers - Provider list, test buttons
- [ ] Logs - Filter selects, refresh button
- [ ] Sandbox - Code editor, run button

**Expected Behavior**:

- All interactive elements are keyboard-accessible
- Focus indicators are clearly visible
- Tab order is logical and predictable
- No keyboard traps (can Tab out of any element)

---

### 3. Motion Sensitivity (prefers-reduced-motion)

**Test Steps**:

**Option A - System Settings (macOS)**:

- [ ] Open System Settings → Accessibility → Display
- [ ] Enable "Reduce motion"
- [ ] Reload app at <http://localhost:3000>
- [ ] Navigate between pages - verify no smooth transitions
- [ ] Hover over buttons - verify no smooth color changes
- [ ] Check loading spinners - verify they still spin (but instant)

**Option B - Browser DevTools**:

- [ ] Open Chrome DevTools (F12)
- [ ] Press Cmd+Shift+P (Mac) or Ctrl+Shift+P (Windows)
- [ ] Type "Show Rendering" and select it
- [ ] Find "Emulate CSS media feature prefers-reduced-motion"
- [ ] Select "prefers-reduced-motion: reduce"
- [ ] Navigate between pages - verify no animations

**Expected Behavior**:

- All CSS transitions reduced to 0.01ms (effectively instant)
- All CSS animations reduced to 0.01ms
- Smooth scrolling disabled
- App remains fully functional, just without motion

---

### 4. Lighthouse Audit (Chrome DevTools)

**Test Steps**:

- [ ] Navigate to <http://localhost:3000>
- [ ] Open Chrome DevTools (F12)
- [ ] Click "Lighthouse" tab
- [ ] Select categories:
  - [x] Performance
  - [x] Accessibility
  - [x] Best Practices
  - [ ] SEO (optional)
- [ ] Click "Analyze page load"
- [ ] Wait for report generation

**Target Scores**:

- **Accessibility**: ≥ 90 (CRITICAL)
- Performance: ≥ 80 (recommended)
- Best Practices: ≥ 80 (recommended)

**If Accessibility < 90**:

- [ ] Review "Accessibility" section in report
- [ ] Fix all Critical and Serious issues
- [ ] Document Moderate/Minor issues for backlog
- [ ] Re-run audit after fixes

**Common Issues to Check**:

- [ ] Missing alt text on images (should be none - we use icons/emojis)
- [ ] Insufficient color contrast (should be none - all pass 4.5:1)
- [ ] Missing ARIA labels (check forms, buttons)
- [ ] Missing form labels (check all inputs have associated labels)

---

### 5. axe DevTools Scan

**Setup**:

- [ ] Install [axe DevTools Extension](https://chrome.google.com/webstore/detail/axe-devtools-web-accessib/lhdoppojpmngadmnindnejefpokejbdd)

**Test Steps**:

- [ ] Navigate to <http://localhost:3000>
- [ ] Open Chrome DevTools (F12)
- [ ] Click "axe DevTools" tab
- [ ] Click "Scan ALL of my page"
- [ ] Wait for scan completion

**Pages to Scan**:

- [ ] Dashboard (/)
- [ ] Chat (/chat)
- [ ] Search (/search)
- [ ] Settings (/settings)
- [ ] Providers (/providers)
- [ ] Logs (/logs)
- [ ] Sandbox (/sandbox)

**Violation Priorities**:

1. **Critical**: Fix immediately (blocks accessibility)
2. **Serious**: Fix before production
3. **Moderate**: Document in backlog
4. **Minor**: Document in backlog

**Expected Result**:

- 0 Critical violations
- 0 Serious violations
- < 5 Moderate violations
- < 10 Minor violations

---

### 6. Screen Reader Testing (Optional but Recommended)

**macOS VoiceOver**:

- [ ] Enable VoiceOver: Cmd+F5
- [ ] Navigate with Control+Option+Arrow keys
- [ ] Test announcements:
  - [ ] Page titles read correctly
  - [ ] Navigation links announced
  - [ ] Form labels read with inputs
  - [ ] Button purposes clear
  - [ ] Error messages announced

**Windows Narrator**:

- [ ] Enable Narrator: Windows+Ctrl+Enter
- [ ] Navigate with Caps Lock+Arrow keys
- [ ] Verify similar announcements as VoiceOver

**NVDA (Windows, free)**:

- [ ] Download from [nvaccess.org](https://www.nvaccess.org/download/)
- [ ] Navigate with Arrow keys, Tab, H (headings), L (links)
- [ ] Verify all interactive elements announced correctly

---

## 📊 Testing Results

### Automated Tests

- ✅ Contrast audit: **ALL PASS** (8/8 combinations)

### Manual Tests

- ⏳ High-contrast mode: **Pending manual verification**
- ⏳ Keyboard navigation: **Pending manual verification**
- ⏳ Motion sensitivity: **Pending manual verification**
- ⏳ Lighthouse audit: **Pending browser test**
- ⏳ axe DevTools scan: **Pending browser test**
- ⏳ Screen reader: **Optional**

---

## 🐛 Issues Found

_(Document any issues discovered during testing)_

### Critical Issues

- None found yet

### Serious Issues

- None found yet

### Moderate Issues

- None found yet

### Minor Issues

- None found yet

---

## 🚀 Sign-Off

Once all tests pass:

- [ ] All automated tests pass ✅
- [ ] High-contrast mode works on all pages
- [ ] Keyboard navigation fully functional
- [ ] Motion sensitivity respects user preference
- [ ] Lighthouse Accessibility score ≥ 90
- [ ] axe DevTools 0 Critical/Serious violations
- [ ] Documentation complete (ACCESSIBILITY.md)

**Tested By**: **\*\*\*\***\_**\*\*\*\***
**Date**: **\*\*\*\***\_**\*\*\*\***
**Status**: ☐ PASS | ☐ FAIL (see issues above)

---

## 📝 Notes

- All tests should be performed on latest Chrome/Edge for consistency
- Test on both standard and high-contrast modes where applicable
- Document any browser-specific issues
- Take screenshots of issues for easier debugging

**Dev Server**: <http://localhost:3000>
**Backend**: <http://localhost:8000>
