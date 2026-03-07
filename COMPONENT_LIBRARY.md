# Goblin Assistant - Component Library

This document describes the comprehensive component library with a systematic, premium design system built for the Goblin Assistant frontend.

## 🎨 Design System Overview

### Warm Palette (Premium Aesthetic)
The design system uses a warm, sophisticated color palette inspired by products like Perplexity and Arc Browser:

- **Primary**: `#d4a574` (Muted Amber/Caramel) — Primary actions and brand color
- **Secondary/Accent**: `#f4967a` (Warm Coral) — Secondary actions and accents
- **CTA**: `#e69e1d` (Warm Orange-Gold) — Call-to-action buttons (bright, intentional)
- **Background**: `#161008` (Warm Deep Brown) — Page background
- **Surface**: `#26211b` (Warm Ash) — Card, input, dropdown backgrounds
- **Text**: `#f8f0e8` (Warm Cream) — Primary text color
- **Semantic**:
  - Success: `#6cc24a` (Soft Green)
  - Warning: `#e8a426` (Warm Gold)
  - Danger: `#e74c3c` (Warm Red)
  - Info: `#8bb3e8` (Warm Blue)

### Design Rules (Enforced Across All Components)

All components follow these three core design rules:

#### 1. **Spacing Rhythm** — 4px Base Unit
```
--space-1: 4px    --space-4: 16px  --space-8: 32px
--space-2: 8px    --space-5: 20px
--space-3: 12px   --space-6: 24px  --space-7: 28px
```
*All padding, margins, and gaps MUST use these values only.*

#### 2. **Border Radius Scale** — 14px Maximum
```
xs: 8px   (--radius-xs)    for small elements
sm: 10px  (--radius-sm)    for subtle curves
md: 12px  (--radius-md)    for standard components ← DEFAULT
lg: 14px  (--radius-lg)    for large components (max)
```
*No hardcoded radius values; no mix of rounded/sharp corners.*

#### 3. **Shadow System** — 4-Level Elevation
```
--shadow-sm:  0 1px 2px rgba(0, 0, 0, 0.08)     (tooltips, subtle)
--shadow-md:  0 4px 8px rgba(0, 0, 0, 0.12)     (cards, dropdowns)
--shadow-lg:  0 10px 20px rgba(0, 0, 0, 0.15)   (dialogs, elevated)
--shadow-xl:  0 20px 40px rgba(0, 0, 0, 0.2)    (modals, top-level)
```
*One consistent shadow vocabulary; no inline shadows.*

---

## Component Categories

### 🎯 Interactive Components (`src/components/ui/`)

All components use **CVA (Class Variance Authority)** for consistent, maintainable variant management.

#### Button
- **Variants**: `primary` | `secondary` | `danger` | `success` | `ghost`
- **Sizes**: `sm` | `md` | `lg` (touch target ≥44px)
- **CVA Features**: Built-in focus ring (outline primary), disabled opacity, smooth transitions
- **Usage**:
  ```tsx
  import { Button } from 'src/components/ui/Button';
  
  // Primary action
  <Button variant="primary" size="md">Save Changes</Button>
  
  // Danger action
  <Button variant="danger">Delete</Button>
  
  // Ghost variant
  <Button variant="ghost" icon={<Trash size={16} />}>Remove</Button>
  ```

#### IconButton
- **Variants**: `primary` | `secondary` | `danger` | `ghost`
- **Sizes**: `sm` | `md` | `lg`
- **Accessibility**: Minimum 44×44px touch target (WCAG)
- **Required**: `aria-label` for screen readers
- **Usage**:
  ```tsx
  import { IconButton } from 'src/components/ui/IconButton';
  
  <IconButton 
    variant="ghost" 
    size="md" 
    icon={<X size={16} />}
    aria-label="Close dialog"
  />
  ```

#### Badge
- **Variants**: `primary` | `secondary` | `success` | `warning` | `danger` | `neutral`
- **Sizes**: `sm` | `md` | `lg`
- **Features**: Status indicators with icon support
- **Usage**:
  ```tsx
  import { Badge } from 'src/components/ui/Badge';
  
  <Badge variant="success" size="sm">Active</Badge>
  <Badge variant="danger" size="md" icon={<AlertCircle size={14} />}>Error</Badge>
  ```

#### Alert
- **Variants**: `info` | `warning` | `danger` | `success`
- **Features**: Dismissible alerts, aria-live regions
- **Accessibility**: Auto-sets `aria-live="assertive"` for dangers
- **Usage**:
  ```tsx
  import { Alert } from 'src/components/ui/Alert';
  
  <Alert variant="danger" title="Error" message="Failed to save." dismissible />
  ```

### 📋 Form Components (`src/components/ui/`)

#### Input
- **Variants**: `sm` | `md` | `lg` sizes
- **States**: `default` | `error` | `success`
- **CVA Features**: Smooth shadow transitions, design-system focus ring
- **Usage**:
  ```tsx
  import { Input } from 'src/components/ui/Input';
  
  <Input 
    placeholder="Enter email..." 
    size="md"
    state={isError ? 'error' : 'default'}
  />
  ```

#### Label (Radix-based)
- **Variants**: `default` | `secondary` | `muted` | `required`
- **Features**: Semantic text hierarchy, required indicator (`*`)
- **Usage**:
  ```tsx
  import { Label } from 'src/components/ui/Label';
  
  <Label variant="default" htmlFor="email">Email Address</Label>
  <Input id="email" />
  ```

#### Select (Radix-based)
- **Features**: Accessible dropdown with scroll buttons, keyboard navigation
- **Styled**: Warm palette, design-system shadows and radius
- **Components**: `Select`, `SelectTrigger`, `SelectContent`, `SelectItem`, `SelectLabel`
- **Usage**:
  ```tsx
  import { 
    Select, SelectTrigger, SelectContent, SelectItem 
  } from 'src/components/ui/Select';
  
  <Select>
    <SelectTrigger>Select an option</SelectTrigger>
    <SelectContent>
      <SelectItem value="opt1">Option 1</SelectItem>
      <SelectItem value="opt2">Option 2</SelectItem>
    </SelectContent>
  </Select>
  ```

### 🎪 Layout Components

#### Card
- **Variants**: `default` | `interactive` | `elevated`
- **Padding**: `none` | `sm` | `md` | `lg`
- **Components**: `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter`
- **Features**: CVA-based, consistent elevation, hover states
- **Usage**:
  ```tsx
  import { Card, CardHeader, CardTitle, CardContent } from 'src/components/ui/Card';
  
  <Card variant="default" padding="lg">
    <CardHeader>
      <CardTitle>Dashboard Summary</CardTitle>
    </CardHeader>
    <CardContent>Content</CardContent>
  </Card>
  ```

#### Grid
- **Variants**: Auto-responsive or fixed column counts
- **Gap**: `xs` | `sm` | `md` | `lg` | `xl` (spacing rhythm applied)
- **Columns**: `auto` (1→4 responsive) | `1` | `2` | `3` | `4`
- **Usage**:
  ```tsx
  import { Grid } from 'src/components/ui/Grid';
  
  <Grid columns="auto" gap="lg">
    <Card>Card 1</Card>
    <Card>Card 2</Card>
  </Grid>
  ```

### 🛠️ Utility Components

#### Dialog (Radix-based)
- **Features**: Accessible modal, focus trapping, animated overlay
- **Components**: `Dialog`, `DialogTrigger`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogFooter`
- **Styling**: Warm palette, design-system shadows and radius
- **Usage**:
  ```tsx
  import { 
    Dialog, DialogTrigger, DialogContent, DialogTitle 
  } from 'src/components/ui/Dialog';
  
  <Dialog>
    <DialogTrigger asChild>
      <Button>Open Dialog</Button>
    </DialogTrigger>
    <DialogContent>
      <DialogTitle>Confirm Action</DialogTitle>
      <div>Dialog content</div>
    </DialogContent>
  </Dialog>
  ```

#### Tooltip
- **Positions**: `top` | `bottom` | `left` | `right`
- **Features**: Keyboard accessible, custom delay
- **Styling**: Design-system palette and shadows
- **Usage**:
  ```tsx
  import { Tooltip } from 'src/components/ui/Tooltip';
  
  <Tooltip content="Help text" position="top">
    <button>Hover me</button>
  </Tooltip>
  ```

---

## CVA Pattern (Class Variance Authority)

### Why CVA?
CVA provides **type-safe**, **maintainable**, **consistent** variant systems without the fragility of string concatenation.

### basic Pattern
```tsx
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

// 1. Define variants
const buttonVariants = cva(
  // Base classes (applied always)
  'inline-flex items-center justify-center gap-2 font-semibold rounded-md transition-all duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2 disabled:opacity-50 disabled:cursor-not-allowed',
  {
    variants: {
      variant: {
        primary: 'bg-primary text-text hover:bg-primary-600 active:bg-primary-600/90 shadow-md hover:shadow-lg',
        secondary: 'bg-surface text-text border border-border hover:bg-surface-hover active:bg-surface-active shadow-sm hover:shadow-md',
      },
      size: {
        sm: 'h-8 px-3 text-sm',
        md: 'h-10 px-4 text-sm',
        lg: 'h-12 px-6 text-base',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

// 2. Extract type info
export type ButtonVariantProps = VariantProps<typeof buttonVariants>;

// 3. Create component with types
export interface ButtonProps 
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'size'>,
          ButtonVariantProps {
  icon?: ReactNode;
  loading?: boolean;
  children: ReactNode;
}

// 4. Use in component
const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', className, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  )
);
```

### Key Principles
- **Base classes first**: All common styles in base (focus ring, disabled state, transitions)
- **Variants for differentiation**: Only styles that change between variants
- **defaultVariants**: Always provide sensible defaults
- **cn() for merging**: Safe class merging with `cn()` utility
- **Type-safe**: Full TypeScript support via `VariantProps`

---

## Migration Guide: Old → New System

### Before (String Concatenation)
```tsx
const variantStyles: Record<string, string> = {
  primary: 'bg-primary text-text-inverse hover:bg-primary-hover shadow-glow-primary',
  secondary: 'bg-surface-hover border...',
};

function Button({ variant = 'primary' }) {
  return <button className={`${baseStyles} ${variantStyles[variant]}`} />;
}
```

### After (CVA)
```tsx
const buttonVariants = cva('...base...', {
  variants: { variant: { primary: '...', secondary: '...' } },
});

function Button({ variant = 'primary' }) {
  return <button className={cn(buttonVariants({ variant }))} />;
}
```

### Benefits
✅ Type-safe variant props (IDE autocomplete)
✅ No runtime errors from typos
✅ Consistent spacing/shadows via design tokens
✅ Composable and maintainable
✅ Enables future theming without refactoring

---

## Design Tokens Reference

### Colors
All colors use CSS variables (`--color-*`) from `src/theme/index.css`:
```tsx
<div className="bg-primary text-text">Primary brand color</div>
<button className="bg-cta">Call-to-action</button>
<div className="border border-border">Divider</div>
```

### Semantic Text Hierarchy
```tsx
<h1 className="text-text-primary font-semibold">Main heading</h1>
<p className="text-text-secondary">Secondary content</p>
<p className="text-text-muted text-sm">Metadata, labels</p>
```

### Spacing Examples
```tsx
<div className="p-4 gap-3">Use --space-4 (16px) padding, 12px gap</div>
<button className="px-3 py-2">Use --space-2 and --space-3</button>
```

### Shadow Examples
```tsx
<div className="shadow-sm">Subtle, tooltips</div>
<div className="shadow-md">Default, cards</div>
<div className="shadow-lg">Elevated, dropdowns</div>
<div className="shadow-xl">Top-level, dialogs</div>
```

### Border Radius Examples
```tsx
<button className="rounded-sm">--radius-sm (10px)</button>
<button className="rounded-md">--radius-md (12px)</button>
<div className="rounded-lg">--radius-lg (14px max)</div>
```

---

## Best Practices

### ✅ DO
- Use design system tokens (colors, spacing, shadows, radius)
- Use CVA for component variants
- Use `cn()` for class merging
- Use `forwardRef` for wrapper components
- Provide `aria-label`, `aria-live`, roles for accessibility
- Keep components focused and composable
- Test with high-contrast mode enabled

### ❌ DON'T
- Hardcode hex colors, RGB values, or inline shadows
- Mix border radius styles (no `rounded-lg` + `rounded-none`)
- Use escaped classes or arbitrary Tailwind values (except in rare cases)
- Nest multiple levels of variant logic
- Create one-off component styles in pages
- Forget about keyboard navigation and focus states

---

## Performance & Accessibility

### Touch Targets
All interactive elements meet WCAG minimum 44×44px targets:
```tsx
// IconButton enforces this automatically
<IconButton size="md" /> // Always ≥ 44×44px

// Button sizes follow the same rule
<Button size="sm" /> // Still accessible
```

### Color Contrast
- **High Contrast Mode**: Separate `:root.goblinos-high-contrast` block with bright warm colors
- **WCAG AAA**: All text/background combinations tested for AAA compliance
- **Semantic Colors**: Success/warning/danger/info colors remain distinguishable without color alone

### Keyboard Navigation
- All interactive components support Tab, Enter, Escape
- Dropdowns (Select) support Arrow keys
- Dialogs trap focus until closed
- Focus ring always visible (outline-primary, 2px, offset-2px)

### Screen Readers
- Components use proper semantic HTML (button, input, label)
- Complex components (Dialog, Select) use ARIA roles and attributes
- `aria-label` required for icon-only buttons
- `aria-live="polite"` for alerts + `aria-live="assertive"` for errors

---

## Theme System

### Default Theme (Warm Palette)
Applied via `:root` CSS variables. Colors optimized for dark mode with warm accents.

### High-Contrast Mode
Enhanced contrast mode available via `document.documentElement.classList.add('goblinos-high-contrast')`:
- Primary: `#ffd89b` (Bright Amber, +higher contrast)
- Accent: `#f98b7d` (Bright Coral)
- CTA: `#ffb020` (Bright Orange)
- Text remains the same, backgrounds stay dark

### Runtime Theme Switching
No component changes needed; CSS variables handle theme switching:
```tsx
// Add class to root to enable HC mode
document.documentElement.classList.toggle('goblinos-high-contrast');

// All components automatically adopt new colors
// No re-renders, pure CSS
```

---

## Component Inventory

### Core UI (`src/components/ui/`)
- ✅ **Button** — CVA-based interactive button
- ✅ **IconButton** — Icon-only button with touch target enforcement
- ✅ **Badge** — Status/tag component with 6 variants
- ✅ **Input** — Text input with size + state variants
- ✅ **Alert** — Dismissible alert with semantic variants
- ✅ **Tooltip** — Accessible tooltip with positioning
- ✅ **Card** — Container with padding and variant support
- ✅ **Grid** — Layout grid with gap + column variants
- ✅ **Select** (Radix) — Accessible dropdown menu
- ✅ **Dialog** (Radix) — Modal dialog with trapping
- ✅ **Label** (Radix) — Form label with semantic variants

### Component Exports
All components exported from `src/components/ui/index.ts` with proper TypeScript types:
```tsx
export type {
  ButtonProps,
  ButtonVariantProps,
  // ... all type exports
};

export {
  Button,
  IconButton,
  Badge,
  // ... all component exports
};
```

---

## Adding New Components

### Step 1: Define CVA
```tsx
// src/components/ui/YourComponent.tsx
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const componentVariants = cva(
  // Base classes only
  'flex items-center transition-all duration-150',
  {
    variants: {
      variant: { /* ... */ },
      size: { /* ... */ },
    },
    defaultVariants: { /* ... */ },
  }
);

export type ComponentVariantProps = VariantProps<typeof componentVariants>;
```

### Step 2: Create Type-Safe Interface
```tsx
export interface YourComponentProps 
  extends HTMLAttributes<HTMLDivElement>,
          ComponentVariantProps {
  children: ReactNode;
}
```

### Step 3: Implement with forwardRef
```tsx
const YourComponent = React.forwardRef<HTMLDivElement, YourComponentProps>(
  ({ variant = 'default', size = 'md', className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(componentVariants({ variant, size }), className)}
      {...props}
    />
  )
);

export default YourComponent;
```

### Step 4: Export from Index
```tsx
// src/components/ui/index.ts
export type { YourComponentProps, ComponentVariantProps };
export { default as YourComponent } from './YourComponent';
```

---

## Testing Components

### Visual Testing (High Contrast)
- Enable HC mode in dev tools: Toggle high-contrast class on root
- Verify colors change without code change
- Check contrast meets WCAG AAA

### Keyboard Testing
- Tab through all interactive elements
- Verify focus ring visible and on-color
- Test Escape to close dialogs/dropdowns

### Accessibility Testing
- Use axe DevTools browser extension
- Verify `aria-label` for icon buttons
- Check semantic HTML (input, button, label)

---

## File Structure

```
src/components/
├── ui/
│   ├── Button.tsx
│   ├── IconButton.tsx
│   ├── Badge.tsx
│   ├── Input.tsx
│   ├── Label.tsx
│   ├── Select.tsx
│   ├── Dialog.tsx
│   ├── Alert.tsx
│   ├── Tooltip.tsx
│   ├── Card.tsx
│   ├── Grid.tsx
│   └── index.ts (exports)
├── pages/
│   └── ... (page-level components)
└── ...

src/theme/
├── index.css (design tokens: colors, spacing, shadows, radius)

src/lib/
├── utils.ts (cn() utility)
├── cva-factory.ts (CVA helpers)
└── ...
```

---

## Common Patterns

### Composable Button Groups
```tsx
<div className="flex gap-2">
  <Button variant="primary">Save</Button>
  <Button variant="secondary">Cancel</Button>
</div>
```

### Card List
```tsx
<Grid columns="auto" gap="lg">
  {items.map(item => (
    <Card key={item.id} variant="interactive">
      <CardTitle>{item.title}</CardTitle>
      <CardContent>{item.content}</CardContent>
    </Card>
  ))}
</Grid>
```

### Form Layout
```tsx
<form>
  <Label htmlFor="email">Email</Label>
  <Input id="email" placeholder="you@example.com" />
  
  <Label htmlFor="password" variant="required">Password</Label>
  <Input id="password" type="password" />
</form>
```

### Dialog with Actions
```tsx
<Dialog>
  <DialogTrigger asChild>
    <Button>Open</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogTitle>Confirm</DialogTitle>
    <div>Are you sure?</div>
    <div className="flex gap-2">
      <Button variant="primary">Yes</Button>
      <Button variant="secondary">No</Button>
    </div>
  </DialogContent>
</Dialog>
```

---

## References

- **CVA Docs**: https://cva.style/docs
- **Radix UI**: https://www.radix-ui.com/
- **Tailwind CSS**: https://tailwindcss.com/
- **WCAG Guidelines**: https://www.w3.org/WAI/WCAG21/quickref/
  <CardContent>Content</CardContent>
</Card>
```

### Variants and Props
Use `class-variance-authority` for variant systems:
```tsx
const componentVariants = cva(
  'base-classes',
  {
    variants: {
      variant: {
        default: 'default-classes',
        secondary: 'secondary-classes',
      },
    },
  }
);
```

## Usage Examples

### Basic Page Structure
```tsx
import { MainLayout } from 'src/components/layout/MainLayout';
import { Button, Badge } from 'src/components/ui/Button';
import { Card } from 'src/components/ui/Card';

export default function Dashboard() {
  return (
    <MainLayout 
      title="Dashboard" 
      subtitle="Welcome back!"
      actions={
        <div className="flex space-x-2">
          <Button variant="outline">Settings</Button>
          <Badge variant="secondary">Beta</Badge>
        </div>
      }
    >
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Analytics</CardTitle>
          </CardHeader>
          <CardContent>
            Your analytics data goes here
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
}
```

### Custom Component
```tsx
import { Button } from 'src/components/ui/Button';
import { Tooltip } from 'src/components/ui/Tooltip';

export function SaveButton({ onSave }: { onSave: () => void }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button onClick={onSave} variant="secondary">
          Save Changes
        </Button>
      </TooltipTrigger>
      <TooltipContent>
        Click to save your changes
      </TooltipContent>
    </Tooltip>
  );
}
```

## Development Guidelines

### Creating New Components
1. **Location**: Place in appropriate subdirectory (`ui/`, `layout/`, etc.)
2. **Naming**: Use PascalCase for component files
3. **Exports**: Export from subdirectory index files
4. **Documentation**: Add JSDoc comments for props
5. **Testing**: Write unit tests for new components

### Component Structure
```tsx
// ComponentName.tsx
import * as React from 'react';
import { clsx } from 'clsx';
import { cva, type VariantProps } from 'class-variance-authority';

// Variants (if needed)
const componentVariants = cva('base-classes', {
  variants: { /* variants */ },
  defaultVariants: { /* defaults */ }
});

// Props interface
export interface ComponentNameProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof componentVariants> {
  // Additional props
}

// Component
export const ComponentName = React.forwardRef<HTMLDivElement, ComponentNameProps>(
  ({ className, variant, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={clsx(componentVariants({ variant, className }))}
        {...props}
      />
    );
  }
);

ComponentName.displayName = 'ComponentName';
```

### Testing Components
```tsx
// ComponentName.test.tsx
import { render, screen } from '@testing-library/react';
import { ComponentName } from './ComponentName';

describe('ComponentName', () => {
  it('renders correctly', () => {
    render(<ComponentName>Test</ComponentName>);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });
});
```

## Integration with Next.js

### App Router
Components work seamlessly with Next.js App Router:
```tsx
// app/dashboard/page.tsx
import { MainLayout } from 'src/components/layout/MainLayout';

export default function DashboardPage() {
  return (
    <MainLayout title="Dashboard">
      <div>Dashboard content</div>
    </MainLayout>
  );
}
```

### Server Components
Most components are client components (use `'use client'` directive when needed):
```tsx
'use client';

import { Button } from 'src/components/ui/Button';
// Component implementation
```

## Performance Considerations

### Code Splitting
- **Lazy Loading**: Use `React.lazy` for heavy components
- **Dynamic Imports**: Import components only when needed
- **Bundle Size**: Keep component dependencies minimal

### Optimization
- **Memoization**: Use `React.memo` for expensive calculations
- **Event Handlers**: Stable function references with `useCallback`
- **State**: Local state when possible, global state for shared data

## Accessibility Standards

### ARIA Labels
Always provide accessible names:
```tsx
<Button aria-label="Close dialog">X</Button>
```

### Keyboard Navigation
Ensure all interactive elements are keyboard accessible:
```tsx
<div 
  role="button"
  tabIndex={0}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleClick();
    }
  }}
>
  Clickable element
</div>
```

### Color Contrast
Components automatically adapt to high contrast mode:
```tsx
// Theme system handles this automatically
<div className="text-foreground">Text</div>
```

## Future Enhancements

### Component Library Goals
- [ ] Form components (Input, Select, Checkbox, Radio)
- [ ] Data display (Table, Chart, Progress)
- [ ] Navigation (Sidebar, Breadcrumbs, Tabs)
- [ ] Feedback (Toast, Modal, Loading)
- [ ] Icons and SVG components

### Advanced Features
- [ ] Component theming with CSS-in-JS
- [ ] Storybook integration for component documentation
- [ ] Design token exports for external use
- [ ] Component composition patterns

## Contributing

1. **Follow Patterns**: Use existing component patterns
2. **TypeScript**: Always provide proper types
3. **Accessibility**: Ensure ARIA compliance
4. **Testing**: Write tests for new components
5. **Documentation**: Update this README for major changes

For more information, see the main [ORGANIZATION.md](./ORGANIZATION.md) file.
