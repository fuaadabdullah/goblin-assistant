---
title: "COMPONENT ARCHITECTURE GUIDELINES"
description: "Component Architecture Guidelines"
---

# Component Architecture Guidelines

## Overview

This document outlines best practices for component architecture in the Goblin Assistant frontend. Following these guidelines ensures maintainable, testable, and scalable React components.

## Component Size Limits

### Maximum Component Size

- **Single file components**: 200 lines maximum
- **Multi-file components**: 300 lines total across all files
- **Exception threshold**: 400 lines requires architecture review

### Why Size Matters

- Components over 200 lines violate single responsibility principle
- Large components are harder to test, debug, and maintain
- Size correlates strongly with complexity and bug density

## Component Organization

### File Structure

```bash
src/components/
├── ComponentName.tsx          # Main component
├── ComponentName.test.tsx     # Unit tests
├── ComponentName.stories.tsx  # Storybook stories
└── subcomponents/             # Related sub-components
    ├── SubComponent.tsx
    └── SubComponent.test.tsx
```

### Component Categories

#### 1. Atomic Components (≤50 lines)

- Single responsibility
- No side effects
- Pure functions preferred
- Examples: Button, Badge, Icon

#### 2. Molecular Components (51-150 lines)

- Combine atomic components
- Handle simple state
- Examples: StatusCard, FormField, Modal

#### 3. Organism Components (151-300 lines)

- Complex state management
- Multiple responsibilities
- Coordinate molecular components
- Examples: Dashboard, ChatInterface

#### 4. Page Components (301+ lines)

- Full page layouts
- Route-level components
- Heavy state coordination
- **Must be broken down** - not acceptable as single files

## Separation of Concerns

### Data Fetching

- Extract API calls into custom hooks
- Use `useEffect` for side effects
- Handle loading/error states in hooks

```typescript
// ✅ Good: Custom hook for data fetching
function useDashboardData() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData()
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  return { data, loading };
}
```

### State Management

- Local state: `useState` for component-specific state
- Shared state: Context or global state management
- Side effects: `useEffect` with proper dependencies

### UI Logic

- Separate presentation from logic
- Use custom hooks for complex UI state
- Keep render functions clean and readable

## Component Composition

### Props Interface

- Define clear TypeScript interfaces
- Use descriptive prop names
- Document optional vs required props

```typescript
interface ComponentProps {
  /** Required data for rendering */
  data: DataType;
  /** Optional callback when action occurs */
  onAction?: (result: ActionResult) => void;
  /** Whether component is in loading state */
  loading?: boolean;
}
```

### Children vs Props

- Use `children` for flexible content
- Use named props for structured data
- Prefer composition over complex prop drilling

### Component Variants

- Use discriminated unions for variants
- Avoid boolean prop explosion
- Document variant behavior

```typescript
type ButtonVariant = 'primary' | 'secondary' | 'danger';

interface ButtonProps {
  variant?: ButtonVariant;
  // ... other props
}
```

## Performance Considerations

### Memoization

- Use `React.memo` for expensive components
- Use `useMemo` for expensive calculations
- Use `useCallback` for event handlers passed to children

### Re-rendering

- Avoid unnecessary re-renders
- Use proper dependency arrays in hooks
- Consider component splitting for isolated updates

## Testing Guidelines

### Test Coverage

- Unit tests for all components
- Integration tests for component interactions
- Visual regression tests for UI components

### Test Structure

```typescript
describe('ComponentName', () => {
  it('renders correctly', () => {
    // Test basic rendering
  });

  it('handles user interactions', () => {
    // Test event handlers
  });

  it('displays loading states', () => {
    // Test loading behavior
  });
});
```

## Accessibility

### ARIA Labels

- Provide descriptive labels for interactive elements
- Use semantic HTML elements
- Test with screen readers

### Keyboard Navigation

- Ensure all interactive elements are keyboard accessible
- Maintain logical tab order
- Provide keyboard shortcuts where appropriate

## Code Quality

### Linting

- All components must pass ESLint rules
- Use Prettier for consistent formatting
- Follow TypeScript strict mode

### Documentation

- JSDoc comments for complex components
- Prop documentation in interfaces
- Usage examples in comments

## Refactoring Process

### When to Refactor

- Component exceeds size limits
- Component has multiple responsibilities
- Component is hard to test
- Component has complex state logic

### Refactoring Steps

1. Identify separation opportunities
2. Extract custom hooks for logic
3. Create sub-components for UI sections
4. Update tests and documentation
5. Verify functionality preserved

### Example Refactoring: Dashboard Component

**Before**: 442-line monolithic component
**After**: Multiple focused components

- `useDashboardData` hook (data fetching)
- `DashboardHeader` component (controls)
- `CostOverviewBanner` component (cost display)
- `StatusCardsGrid` component (health cards)
- `DashboardError` component (error handling)

## Migration Strategy

### Gradual Adoption

1. Apply guidelines to new components immediately
2. Refactor existing components during feature work
3. Set up automated size monitoring
4. Regular architecture reviews

### Tooling

- ESLint rules for component size limits
- Pre-commit hooks for quality checks
- Automated complexity analysis
- Component usage analytics

## Monitoring & Metrics

### Size Tracking

- Track component sizes in CI/CD
- Alert on components exceeding limits
- Monitor refactoring progress

### Quality Metrics

- Test coverage percentage
- Bundle size impact
- Performance benchmarks
- Accessibility scores

## Conclusion

Following these guidelines ensures:

- **Maintainable** components that are easy to understand
- **Testable** components with clear boundaries
- **Performant** components optimized for React
- **Accessible** components usable by all users
- **Scalable** architecture that grows with the application

Regular review and adherence to these guidelines will maintain high code quality across the Goblin Assistant frontend.
