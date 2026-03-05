# UI Component Library

**Location**: `src/components/ui/`
**Purpose**: Centralized, reusable UI atoms to eliminate duplicate styles and ensure consistency.

---

## 📦 Available Components

### Button

**Import**: `import { Button } from './ui'`

Unified button component with variants and sizes. Replaces duplicate button styles across the app.

**Props**:

```typescript
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'danger' | 'success' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  fullWidth?: boolean;
  icon?: ReactNode;
  loading?: boolean;
  disabled?: boolean;
  children: ReactNode;
}
```

**Example**:

```tsx

// Primary button with icon
<Button variant="primary" icon="🔄" onClick={handleRefresh}>
  Refresh
</Button>

// Full-width danger button with loading state
<Button variant="danger" fullWidth loading={isLoading}>
  Delete
</Button>

// Small ghost button
<Button variant="ghost" size="sm">
  Cancel
</Button>
```

**Variants**:

- `primary` - Primary action (green glow)
- `secondary` - Secondary action (border, no glow)
- `danger` - Destructive action (red glow)
- `success` - Success action (green, no glow)
- `ghost` - Minimal button (border only)

---

### Badge

**Import**: `import { Badge } from './ui'`

Status chip/badge component with color-coded variants. Replaces inline badge styles.

**Props**:

```typescript
interface BadgeProps {
  variant?: 'success' | 'warning' | 'danger' | 'neutral' | 'primary';
  size?: 'sm' | 'md';
  icon?: ReactNode;
  children: ReactNode;
}
```

**Example**:

```tsx

// Success badge with icon
<Badge variant="success" icon="✓">
  Healthy
</Badge>

// Warning badge
<Badge variant="warning" icon="⚠">
  Degraded
</Badge>

// Medium-sized primary badge
<Badge variant="primary" size="md">
  Active
</Badge>
```

**Variants**:

- `success` - Green (healthy, completed)
- `warning` - Orange (degraded, pending)
- `danger` - Red (down, error)
- `neutral` - Gray (unknown, inactive)
- `primary` - Cyan (info, default)

---

### IconButton

**Import**: `import { IconButton } from './ui'`

Icon-only button with consistent sizing and variants. Ensures minimum 44x44px touch target.

**Props**:

```typescript
interface IconButtonProps {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  icon: ReactNode;
  'aria-label': string; // Required for accessibility
}
```

**Example**:

```tsx

// Ghost icon button (most common)
<IconButton
  variant="ghost"
  icon="✕"
  aria-label="Dismiss alert"
  onClick={handleDismiss}
/>

// Primary icon button
<IconButton
  variant="primary"
  size="lg"
  icon="+"
  aria-label="Add item"
/>
```

**Sizes**:

- `sm` - 32x32px (8x8)
- `md` - 40x40px (10x10) - default
- `lg` - 48x48px (12x12)

---

### Grid

**Import**: `import { Grid } from './ui'`

Wrapper for responsive grid layouts. Uses `.grid-auto-fit` utility by default.

**Props**:

```typescript
interface GridProps {
  children: ReactNode;
  gap?: 'sm' | 'md' | 'lg';
  autoFit?: boolean; // Use grid-auto-fit utility (default: true)
}
```

**Example**:

```tsx

// Auto-responsive card grid
<Grid gap="md">
  <StatusCard {...} />
  <StatusCard {...} />
  <StatusCard {...} />
</Grid>

// Custom grid with large gap
<Grid gap="lg" autoFit={false} className="grid-cols-3">
  {/* Manual columns */}
</Grid>
```

**Gap Sizes**:

- `sm` - 8px (gap-2)
- `md` - 16px (gap-4) - default
- `lg` - 24px (gap-6)

---

### Alert

**Import**: `import { Alert } from './ui'`

Unified alert/banner component for errors, warnings, info messages. Replaces duplicate banners.

**Props**:

```typescript
interface AlertProps {
  variant?: 'info' | 'warning' | 'danger' | 'success';
  title?: string;
  message: string | ReactNode;
  dismissible?: boolean;
  onDismiss?: () => void;
  icon?: ReactNode;
}
```

**Example**:

```tsx

// Danger alert with custom content
<Alert
  variant="danger"
  title="Dashboard Error"
  message={
    <>
      <p>{error}</p>
      <Button onClick={retry}>Retry</Button>
    </>
  }
/>

// Dismissible warning alert
<Alert
  variant="warning"
  message="Data may be outdated"
  dismissible
  onDismiss={() => setError(null)}
/>

// Info alert with custom icon
<Alert
  variant="info"
  icon="💡"
  message="Tip: Enable auto-refresh for real-time updates"
/>
```

**Variants**:

- `info` - Blue (informational)
- `warning` - Orange (warnings)
- `danger` - Red (errors, critical)
- `success` - Green (success messages)

**Accessibility**:

- `role="alert"` for screen readers
- `aria-live="assertive"` for danger (interrupts)
- `aria-live="polite"` for others (non-interrupting)

---

### Card

**Import**: `import { Card } from './ui'`

Primitive container component (already exists, re-exported for convenience).

**Props**:

```typescript
interface CardProps {
  padded?: boolean;
  bordered?: boolean;
  radius?: 'sm' | 'md' | 'lg';
  elevation?: 'none' | 'card';
  children: ReactNode;
}
```

**Example**:

```tsx

// Standard card
<Card padded bordered radius="md">
  <h3>Card Title</h3>
  <p>Card content</p>
</Card>

// Card with elevation
<Card padded bordered elevation="card">
  Content with shadow
</Card>
```

---

## 🔧 Usage Guidelines

### Before (Duplicate Styles)

```tsx
// ❌ Inline styles repeated everywhere
<button className="px-4 py-2 bg-primary text-text-inverse rounded-lg hover:brightness-110 shadow-glow-primary transition-all">
  Click Me
</button>

<button className="px-4 py-2 bg-danger hover:brightness-110 text-text-inverse rounded-lg shadow-glow-cta transition-all">
  Delete
</button>

<div className="bg-danger/10 border border-danger rounded-lg p-4">
  <span className="text-danger">Error message</span>
</div>
```

### After (Component Library)

```tsx

// ✅ Consistent, reusable components
<Button variant="primary">
  Click Me
</Button>

<Button variant="danger">
  Delete
</Button>

<Alert variant="danger" message="Error message" />
```

---

## 🎯 Benefits

1. **Consistency**: All buttons, badges, alerts use same styles
2. **Maintainability**: Update one place, changes everywhere
3. **Accessibility**: Built-in ARIA attributes and focus states
4. **Type Safety**: TypeScript props with autocomplete
5. **Smaller Bundle**: Reused components = less CSS duplication
6. **Developer Experience**: Import once, use anywhere

---

## 🚀 Migration Checklist

Components already using UI library:

- ✅ **StatusCard** - Uses Badge component
- ✅ **EnhancedDashboard** - Uses Button, Alert, Grid

Components pending migration:

- ⏳ **TaskExecution** - Replace inline button styles
- ⏳ **Orchestration** - Replace inline button/alert styles
- ⏳ **HealthCard** - Replace inline button styles
- ⏳ **Navigation** - Could use Button for nav items
- ⏳ **KeyboardShortcutsHelp** - Replace kbd styles with Badge

---

## 📝 Component Development Guidelines

### When to Create a New Component

Create a new UI atom when:

1. **Pattern repeats 3+ times** across different files
2. **Styling is consistent** (same colors, spacing, behavior)
3. **Behavior is reusable** (hover, focus, disabled states)

### When to Use Props vs. className

**Use Props For**:

- Semantic variants (primary, danger, success)
- Size variations (sm, md, lg)
- Common modifiers (fullWidth, loading, disabled)

**Use className For**:

- One-off adjustments
- Layout-specific styles (margin, positioning)
- Component-specific overrides

### Example: Button Component Design

```typescript
// ✅ Good: Semantic props + className for overrides
<Button variant="primary" fullWidth className="mt-4">
  Submit
</Button>

// ❌ Bad: All styling via className (defeats purpose)
<Button className="bg-primary text-white px-4 py-2 rounded">
  Submit
</Button>
```

---

## 🔄 Replacing Duplicates

### Step 1: Identify Pattern

Search for repeated className patterns:

```bash

grep -r "bg-primary.*rounded-lg.*hover:brightness" src/
```

### Step 2: Extract to Component

Create reusable component in `src/components/ui/`:

```tsx
// Button.tsx
export default function Button({ variant, children, ...props }) {
  const styles = variantStyles[variant];
  return (
    <button className={`base-styles ${styles}`} {...props}>
      {children}
    </button>
  );
}
```

### Step 3: Replace Usage

```tsx
// Before
<button className="px-4 py-2 bg-primary...">Click</button>;

// After
import { Button } from './ui';
<Button variant="primary">Click</Button>;
```

### Step 4: Update Imports

Add to `src/components/ui/index.ts`:

```typescript
export { default as Button } from './Button';
export type { ButtonProps } from './Button';
```

---

## 📚 Related Documentation

- **Design System**: `src/theme/index.css` - Theme tokens and variables
- **Typography Scale**: `src/index.css` - Font sizes and line heights
- **Responsive Grid**: `.grid-auto-fit` utility in `src/index.css`
- **Accessibility**: WCAG 2.1 AA compliance guidelines

---

## 🎨 Design Tokens

Components use centralized design tokens from `src/theme/index.css`:

### Colors

```css
--primary: #00ff88 --accent: #00d9ff --danger: #ff4466 --warning: #ffaa00 --success: #00ff88;
```

### Spacing

```css
--space-1: 4px --space-2: 8px --space-3: 12px --space-4: 16px;
```

### Radii

```css
--radius-sm: 4px --radius-md: 8px --radius-lg: 12px;
```

### Elevation

```css
--shadow-card: 0 1px 2px rgba(0, 0, 0, 0.3) --glow-primary: 0 6px 24px var(--primary)
  --glow-accent: 0 6px 24px var(--accent) --glow-cta: 0 6px 24px var(--danger);
```

---

## 🧪 Testing

### Manual Testing

1. Check all variants render correctly
2. Verify hover/focus states
3. Test disabled states
4. Confirm keyboard navigation
5. Screen reader announcements (ARIA)

### Automated Testing (Future)

```typescript

// Example: Button.test.tsx
describe('Button', () => {
  it('renders primary variant', () => {
    render(<Button variant="primary">Click</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-primary');
  });

  it('shows loading spinner', () => {
    render(<Button loading>Submit</Button>);
    expect(screen.getByText('⟳')).toHaveClass('animate-spin');
  });
});
```

---

**Last Updated**: December 2, 2025
**Status**: Core components complete, migration in progress
**Maintainer**: See `.github/copilot-instructions.md`
