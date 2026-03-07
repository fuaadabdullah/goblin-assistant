# Design Tokens Reference

Complete visual and technical reference for the Goblin Assistant design system.

## Color Palette

### Default Theme (Warm Aesthetic)

#### Primary & Brand
| Token | Value | Usage | Notes |
|-------|-------|-------|-------|
| `--color-primary` | `#d4a574` | Main actions, brand highlight | Muted amber, warm caramel tone |
| `--color-primary-hover` | `#c09460` | Button hover state | Slightly darker |
| `--color-primary-active` | `#b08a55` | Button active/pressed | Even darker |

#### Secondary & Accent
| Token | Value | Usage | Notes |
|-------|-------|-------|-------|
| `--color-accent` | `#f4967a` | Secondary actions, accent elements | Warm coral, balances primary |
| `--color-accent-hover` | `#e87d62` | Hover state | Deeper coral |

#### Call-to-Action
| Token | Value | Usage | Notes |
|-------|-------|-------|-------|
| `--color-cta` | `#e69e1d` | High-priority actions | Warm orange-gold, intentional bright |

#### Semantic States
| Token | Value | Usage | Notes |
|-------|-------|-------|-------|
| `--color-success` | `#6cc24a` | Success messages, validation | Soft green |
| `--color-warning` | `#e8a426` | Warning messages | Warm gold (replaces pure yellow) |
| `--color-danger` | `#e74c3c` | Error messages, destructive actions | Warm red |
| `--color-info` | `#8bb3e8` | Informational messages | Warm blue |

#### Neutral Background
| Token | Value | Usage | Notes |
|-------|-------|-------|-------|
| `--color-bg` | `#161008` | Page background | Deep warm brown (instead of cool blue) |
| `--color-surface` | `#26211b` | Card, input, dropdown backgrounds | Warm ash, higher contrast than bg |
| `--color-surface-hover` | `#3a342f` | Card/element hover state | Further lifted |
| `--color-surface-active` | `#4a4239` | Card/element active state | More contrast |

#### Text
| Token | Value | Usage | Notes |
|-------|-------|-------|-------|
| `--color-text` | `#f8f0e8` | Primary text | Warm cream (instead of cool cyan) |
| `--color-text-secondary` | `#d4ccc0` | Secondary text, subtitles | Slightly muted |
| `--color-text-muted` | `#a89f96` | Metadata, labels, disabled text | Further muted |
| `--color-text-inverse` | `#161008` | Text on light backgrounds (rare) | Dark brown |

#### Borders & Dividers
| Token | Value | Usage | Notes |
|-------|-------|-------|-------|
| `--color-border` | `rgba(248, 240, 232, 0.12)` | Input borders, dividers | Warm cream with opacity |
| `--color-border-hover` | `rgba(248, 240, 232, 0.2)` | Focus state borders | Slightly more opaque |

### High-Contrast Theme

Enabled via `document.documentElement.classList.add('goblinos-high-contrast')` or `:root.goblinos-high-contrast` in CSS.

#### Bright Variants (Increased Contrast)
| Token | Default | HC Mode | Difference |
|-------|---------|---------|-----------|
| `--color-primary` | `#d4a574` | `#ffd89b` | Much brighter, higher contrast |
| `--color-accent` | `#f4967a` | `#f98b7d` | Slightly brighter |
| `--color-cta` | `#e69e1d` | `#ffb020` | Brighter, more saturated |

#### HC Text & Background
- `--color-text`: `#f8f0e8` (unchanged)
- `--color-bg`: `#161008` (unchanged)
- `--color-surface`: `#26211b` (unchanged)

**Result**: Semantic colors (primary, accent, cta, success, warning, danger) become visually brighter and more distinct while maintaining dark background and warm tone. WCAG AAA contrast compliance maintained.

---

## Spacing Scale

All spacing uses **4px base unit** for consistency.

### Scale Values
```css
--space-1: 4px      /* Extra small: icon padding */
--space-2: 8px      /* Small: tight items */
--space-3: 12px     /* Small-medium: standard padding */
--space-4: 16px     /* Medium: default padding */
--space-5: 20px     /* Medium-large: card padding */
--space-6: 24px     /* Large: section padding */
--space-7: 28px     /* Extra large: major sections */
--space-8: 32px     /* Extra large: gaps */
```

### Usage Examples

**Icon Spacing**
```tsx
<button className="p-2">Icon padding (8px)</button>              // --space-2
<button className="px-2 py-1">Icon with label (4-8px)</button> // --space-1, --space-2
```

**Cards**
```tsx
<Card className="p-6">
  <CardTitle className="mb-4">                    {/* --space-4 = 16px gap */}
    Dashboard
  </CardTitle>
  <CardContent className="flex gap-3">            {/* --space-3 = 12px gap */}
    ...
  </CardContent>
</Card>
```

**Grid Layouts**
```tsx
<Grid gap="lg">  {/* Translates to gap-6 = 24px */}
  <Card className="p-5">                          {/* --space-5 = 20px padding */}
    ...
  </Card>
</Grid>
```

---

## Shadow System

4-level elevation hierarchy. **One and only one** shadow system (no arbitrary shadows).

### Elevation Levels

#### Level 1: Subtle (Tooltips, Subtle Elements)
```css
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.08)
```
- **When to use**: Tooltips, badges, small overlays
- **Visual**: Very subtle, barely visible
- **Example**: Tooltip near cursor

#### Level 2: Standard (Cards, Dropdowns)
```css
--shadow-md: 0 4px 8px rgba(0, 0, 0, 0.12)
```
- **When to use**: Cards, dropdowns, hover states
- **Visual**: Clear shadow, raised appearance
- **Example**: Card component, Select dropdown content

#### Level 3: Elevated (Dialogs, Elevated Modals)
```css
--shadow-lg: 0 10px 20px rgba(0, 0, 0, 0.15)
```
- **When to use**: Modals, important dialogs
- **Visual**: Strong shadow, top-level appearance
- **Example**: Dialog, Alert

#### Level 4: Top-Level (Modals, Overlays)
```css
--shadow-xl: 0 20px 40px rgba(0, 0, 0, 0.2)
```
- **When to use**: Top-level modals, critical overlays
- **Visual**: Very strong shadow, definitely floating
- **Example**: Main modal with backdrop

### Visual Comparison

```
--shadow-sm   ▭  minimal lift
--shadow-md   ▬▬ moderate lift
--shadow-lg   ▬▬▬ strong lift
--shadow-xl   ▬▬▬▬ extreme lift (max)
```

### Usage Pattern

```tsx
// Tooltip or small element
<div className="shadow-sm">Tooltip</div>

// Card or dropdown
<Card className="shadow-md">
  <CardContent/>
</Card>

// Modal dialog
<Dialog>
  <DialogContent className="shadow-lg">
    ...
  </DialogContent>
</Dialog>

// Top-level modal (rare)
<Modal className="shadow-xl">...</Modal>
```

### Hover Progression (Buttons)
```tsx
// On hover, elements progress upward:
<Button className="shadow-md hover:shadow-lg">
  // Starts at --shadow-md
  // Lifts to --shadow-lg on hover
</Button>
```

---

## Border Radius Scale

Maximum **14px** border radius. Consistent, predictable scales.

### Scale Values
```css
--radius-xs: 8px   /* Small corners: icon buttons, small badges */
--radius-sm: 10px  /* Subtle corners: input fields */
--radius-md: 12px  /* Standard corners: cards, buttons (DEFAULT) */
--radius-lg: 14px  /* Large corners: large components (MAX) */
```

### Visual Reference

**xs (8px)** — Subtle, nearly sharp
```
┌─────┐
│     │
└─────┘
```

**sm (10px)** — Slightly rounded
```
┏━━━━━┓
┃     ┃
┗━━━━━┛
```

**md (12px)** — Standard (DEFAULT)
```
╭─────╮
│     │
╰─────╯
```

**lg (14px)** — Rounded (MAX)
```
╭─────╮
│  •  │
╰─────╯
```

### Component Defaults

| Component | Radius | Notes |
|-----------|--------|-------|
| Button | `rounded-md` (12px) | Standard, comfortable |
| IconButton | `rounded-md` (12px) | Consistent with Button |
| Input | `rounded-sm` (10px) | Slightly less rounded |
| Card | `rounded-lg` (14px) | Large, premium feel |
| Badge | `rounded-sm` (10px) | Small, tight |
| Dialog | `rounded-lg` (14px) | Large, modal |
| Tooltip | `rounded-sm` (10px) | Small popup |
| Dropdown | `rounded-md` (12px) | Standard |

### Usage
```tsx
// Explicitly override if needed (rare)
<div className="rounded-lg">Large radius (14px max)</div>
<div className="rounded-md">Standard (12px DEFAULT)</div>
<div className="rounded-sm">Small (10px)</div>
<div className="rounded-xs">Subtle (8px)</div>

// Never mix: ❌ AVOID
<div className="rounded-lg rounded-none">Conflicting!</div>
```

---

## Typography Scale

Semantic text hierarchy (from `src/theme/index.css` + Tailwind defaults).

### Hierarchy Levels

| Level | Class | Size | Weight | Color | Usage |
|-------|-------|------|--------|-------|-------|
| **H1** | `text-2xl font-bold` | 28px | Bold (700) | text-primary | Page titles |
| **H2** | `text-xl font-semibold` | 24px | Semibold (600) | text-primary | Section titles |
| **H3** | `text-lg font-semibold` | 20px | Semibold (600) | text-primary | Subsection titles |
| **Body Large** | `text-base` | 16px | Normal (400) | text-primary | Primary content |
| **Body Default** | `text-sm` | 14px | Normal (400) | text-secondary | Secondary content |
| **Body Small** | `text-xs` | 12px | Normal (400) | text-muted | Metadata, labels |
| **Label** | `text-sm font-semibold` | 14px | Semibold (600) | text-primary | Form labels |

### Semantic Color Classes

```tsx
{/* Primary text - main content */}
<p className="text-text-primary">Main paragraph</p>

{/* Secondary text - supporting content */}
<p className="text-text-secondary">Secondary paragraph</p>

{/* Muted text - labels, metadata */}
<p className="text-text-muted text-xs">Timestamp</p>

{/* Inverse text - on light backgrounds (rare) */}
<div className="bg-primary">
  <p className="text-text-inverse">Text on colored background</p>
</div>
```

---

## Focus & Interaction States

### Focus Ring (Universal)
Applied via `focus-visible:outline`:
```css
focus-visible:outline
focus-visible:outline-2
focus-visible:outline-primary
focus-visible:outline-offset-2
```

**Visual**:
```
────────────────
│  ▭▭▭▭▭▭▭▭▭  │  ← 2px outline
│  | Button |  │
│  ▭▭▭▭▭▭▭▭▭  │  ← 2px offset
────────────────
```

- **Color**: Primary (`#d4a574` or `#ffd89b` in HC)
- **Width**: 2px
- **Offset**: 2px (space between element and ring)

### Disabled State
```css
disabled:opacity-50
disabled:cursor-not-allowed
```

### Hover State (Buttons)
```tsx
<Button>
  hover:shadow-lg           {/* Shadow elevation */}
  hover:brightness-110     {/* Slight lighten */}
</Button>
```

### Active/Pressed State
```tsx
active:brightness-90       {/* Darker when pressed */}
active:shadow-md           {/* Subtle lift reduction */}
```

---

## Accessibility Checklist

- [ ] All interactive elements are ≥44×44px (touch target)
- [ ] Focus ring is always visible (test with Tab key)
- [ ] Color contrast ≥4.5:1 for text (WCAG AA)
- [ ] Color contrast ≥7:1 for text (WCAG AAA)
- [ ] High-contrast mode tested and verified
- [ ] No color-only information (always pair with icons/text)
- [ ] `aria-label` on icon-only buttons
- [ ] Keyboard navigation fully functional
- [ ] Screen reader announces states (alerts have `aria-live`)

---

## Implementation Checklist

When implementing new components:

- [ ] Use only values from this token reference
- [ ] No hardcoded colors, shadows, or radius values
- [ ] Use CVA for variant management
- [ ] Use `cn()` for class merging
- [ ] Include focus ring styling
- [ ] Test in high-contrast mode
- [ ] Verify touch targets ≥44×44px
- [ ] Export proper TypeScript types
- [ ] Document in COMPONENT_LIBRARY.md

---

## Migration Checklist (Old System → New)

If updating existing components:

- [ ] Replace arbitrary shadows with design system (sm/md/lg/xl)
- [ ] Replace hardcoded colors with CSS variable classes (primary, accent, cta, success, warning, danger)
- [ ] Replace arbitrary radius with scale (xs/sm/md/lg)
- [ ] Replace manual variant Records with CVA
- [ ] Verify spacing uses 4px scale (space-1 through space-8)
- [ ] Add proper VariantProps exports
- [ ] Test focus ring and disabled states
- [ ] Update index.ts exports

---

## Quick Reference (Copy-Paste)

### Warm Color Classes
```tsx
bg-primary              {/* #d4a574 main brand */}
bg-accent               {/* #f4967a secondary accent */}
bg-cta                  {/* #e69e1d call-to-action */}
bg-success              {/* #6cc24a validation */}
bg-warning              {/* #e8a426 warnings */}
bg-danger               {/* #e74c3c errors */}
bg-info                 {/* #8bb3e8 info */}

text-text              {/* #f8f0e8 primary text */}
text-text-secondary    {/* #d4ccc0 secondary text */}
text-text-muted        {/* #a89f96 muted text */}

bg-bg                  {/* #161008 page background */}
bg-surface             {/* #26211b card/input background */}
```

### Shadow Classes
```tsx
shadow-sm             {/* Tooltips */}
shadow-md             {/* Cards (DEFAULT) */}
shadow-lg             {/* Dialogs */}
shadow-xl             {/* Top-level modals */}

hover:shadow-lg       {/* Button hover progression */}
```

### Radius Classes
```tsx
rounded-xs           {/* 8px - small elements */}
rounded-sm           {/* 10px - inputs, badges */}
rounded-md           {/* 12px - buttons, cards (DEFAULT) */}
rounded-lg           {/* 14px - large components (MAX) */}
```

### Spacing Classes
```tsx
p-2    {/* 8px padding (--space-2) */}
p-3    {/* 12px padding (--space-3) */}
p-4    {/* 16px padding (--space-4) DEFAULT */}
p-5    {/* 20px padding (--space-5) */}
p-6    {/* 24px padding (--space-6) */}

gap-3  {/* 12px gap (--space-3) */}
gap-4  {/* 16px gap (--space-4) */}
gap-6  {/* 24px gap (--space-6) */}
```

---

## Debug Mode (WIP)

To visualize design tokens during development:

1. Open DevTools console
2. Run: `window.toggleDesignTokenOverlay?.()`
3. Token values appear as tooltips on hover
4. Test HC mode toggle

---

**Last Updated**: Phase 6 Design System Completion
**Scope**: Applies to all components in `src/components/ui/`
**Maintenance**: Update this document when adding new tokens or changing scale values
