# Goblin Assistant - Component Library

This document describes the comprehensive component library built for the Goblin Assistant frontend.

## Overview

The component library follows modern React patterns with TypeScript, Radix UI primitives, and a design system built on top of Tailwind CSS. All components are organized in the `src/components/` directory with clear separation of concerns.

## Component Categories

### 🎨 UI Components (`src/components/ui/`)

Reusable, low-level components built with Radix UI for accessibility and consistency.

#### Button
- **Variants**: `default`, `destructive`, `outline`, `secondary`, `ghost`, `link`
- **Sizes**: `default`, `sm`, `lg`, `icon`
- **Features**: Full Radix UI integration, accessible, customizable
- **Usage**:
  ```tsx
  import { Button } from 'src/components/ui/Button';
  
  <Button variant="primary" size="lg">Click me</Button>
  ```

#### Badge
- **Variants**: `default`, `secondary`, `destructive`, `outline`
- **Features**: Status indicators, tags, labels
- **Usage**:
  ```tsx
  import { Badge } from 'src/components/ui/Badge';
  
  <Badge variant="secondary">New Feature</Badge>
  ```

#### Tooltip
- **Features**: Accessible tooltips with positioning
- **Components**: `Tooltip`, `TooltipTrigger`, `TooltipContent`, `TooltipProvider`
- **Usage**:
  ```tsx
  import { Tooltip, TooltipTrigger, TooltipContent } from 'src/components/ui/Tooltip';
  
  <Tooltip>
    <TooltipTrigger>Hover me</TooltipTrigger>
    <TooltipContent>This is a tooltip</TooltipContent>
  </Tooltip>
  ```

#### Card
- **Components**: `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter`
- **Features**: Flexible card layout system
- **Usage**:
  ```tsx
  import { Card, CardHeader, CardTitle, CardContent } from 'src/components/ui/Card';
  
  <Card>
    <CardHeader>
      <CardTitle>Card Title</CardTitle>
    </CardHeader>
    <CardContent>
      Card content goes here
    </CardContent>
  </Card>
  ```

### 🏗️ Layout Components (`src/components/layout/`)

High-level layout components for page structure and organization.

#### Header
- **Features**: Sticky header with theme awareness
- **Props**: `title`, `subtitle`, `actions`, `className`
- **Theme Integration**: Shows high contrast badge when enabled
- **Usage**:
  ```tsx
  import { Header } from 'src/components/layout/Header';
  
  <Header 
    title="Dashboard" 
    subtitle="Overview of your projects"
    actions={<Button>Settings</Button>}
  />
  ```

#### MainLayout
- **Features**: Complete page layout with header and main content area
- **Props**: `children`, `title`, `subtitle`, `actions`, `className`
- **Responsive**: Container-based responsive design
- **Usage**:
  ```tsx
  import { MainLayout } from 'src/components/layout/MainLayout';
  
  <MainLayout title="Dashboard" actions={<Button>Export</Button>}>
    <div>Your page content here</div>
  </MainLayout>
  ```

### 🛡️ Error Components (`src/components/`)

Error handling components for robust user experience.

#### ErrorBoundary
- **Features**: Catches React errors and displays fallback UI
- **Customizable**: Accepts custom fallback component
- **Usage**: Wrap components that might throw errors

#### ErrorFallback
- **Features**: Default error display component
- **Development**: Shows error details in dev mode
- **Accessibility**: Screen reader friendly

## Design System Integration

### Theme System
All components integrate with the theme system:
- **Design Tokens**: Colors, spacing, typography from `src/theme/index.ts`
- **High Contrast**: Automatic support for high contrast mode
- **Theme Switching**: Components adapt to theme changes

### Accessibility
- **Radix UI**: All interactive components use Radix for ARIA compliance
- **Keyboard Navigation**: Full keyboard support
- **Screen Readers**: Proper semantic markup and labels

### Responsive Design
- **Tailwind CSS**: Mobile-first responsive utilities
- **Container System**: Consistent spacing and layout
- **Breakpoints**: sm, md, lg, xl breakpoints

## Component Patterns

### TypeScript First
All components are fully typed:
```tsx
interface ComponentProps {
  variant?: 'default' | 'secondary';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  children: React.ReactNode;
}
```

### Composition
Components are designed for composition:
```tsx
<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Description</CardDescription>
  </CardHeader>
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
