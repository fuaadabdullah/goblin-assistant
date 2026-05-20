/**
 * CVA Factory - Helper functions for consistent component styling
 * Reduces boilerplate by providing pre-configured base classes and variants
 * 
 * Design system rules enforced:
 * - One focus ring style (outline primary color)
 * - One disabled state handling
 * - Consistent transitions
 * - Design-system-first (no escaped classes)
 */

import { cva, type VariantProps } from 'class-variance-authority';

/**
 * Standard focus ring classes for keyboard navigation
 * Used consistently across all interactive components
 */
const FOCUS_RING = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2';

/**
 * Standard disabled state styling
 * Applies opacity reduction and cursor not-allowed
 */
const DISABLED_STATE = 'disabled:opacity-50 disabled:cursor-not-allowed';

/**
 * Standard transition applied to all interactive components
 * Smooth 150ms transitions for all property changes
 */
const TRANSITION = 'transition-all duration-150';

/**
 * Create a button variant definition with sensible defaults
 * 
 * Usage:
 * ```tsx
 * const buttonVariants = cva(
 *   `inline-flex items-center justify-center font-medium rounded-md ${getBaseComponentClasses()}`,
 *   {
 *     variants: {
 *       variant: {
 *         primary: 'bg-primary text-text hover:bg-primary-600',
 *         secondary: 'bg-surface text-text border border-border hover:bg-surface-hover',
 *       },
 *       size: {
 *         sm: 'h-8 px-3 text-sm',
 *         md: 'h-10 px-4 text-base',
 *         lg: 'h-12 px-6 text-lg',
 *       },
 *     },
 *   }
 * );
 * ```
 */
export function getBaseComponentClasses(): string {
  return `${FOCUS_RING} ${DISABLED_STATE} ${TRANSITION}`;
}

/**
 * Create a button-style component with common defaults
 * Returns CVA function that handles variant + size combinations
 * 
 * Pre-configured:
 * - Focus ring
 * - Disabled state
 * - Smooth transitions
 * - Inline flex layout
 * - Proper font sizing
 * - Rounded corners (radius-md)
 */
export const buttonBase = cva(
  `inline-flex items-center justify-center gap-2 font-medium rounded-md ${FOCUS_RING} ${DISABLED_STATE} ${TRANSITION}`,
  {
    variants: {
      variant: {
        primary: 'bg-primary text-text hover:bg-primary-600 active:bg-primary-600/90 shadow-md hover:shadow-lg',
        secondary: 'bg-surface text-text border border-border hover:bg-surface-hover hover:border-primary/50 active:bg-surface-active shadow-sm hover:shadow-md',
        accent: 'bg-accent text-text hover:bg-accent-600 active:bg-accent-600/90 shadow-md hover:shadow-lg',
        danger: 'bg-danger text-text hover:bg-danger/90 active:bg-danger/80 shadow-md hover:shadow-lg',
        ghost: 'text-text hover:bg-surface/50 active:bg-surface/70',
      },
      size: {
        sm: 'h-8 px-3 text-sm',
        md: 'h-10 px-4 text-base',
        lg: 'h-12 px-6 text-lg',
        xl: 'h-14 px-8 text-lg',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

export type ButtonVariants = VariantProps<typeof buttonBase>;

/**
 * Create an icon button variant (fixed square size)
 * Pre-configured for 44x44px minimum touch target
 */
export const iconButtonBase = cva(
  `inline-flex items-center justify-center font-medium rounded-md ${FOCUS_RING} ${DISABLED_STATE} ${TRANSITION} ${getMinTouchTarget()}`,
  {
    variants: {
      variant: {
        primary: 'bg-primary text-text hover:bg-primary-600 active:bg-primary-600/90 shadow-sm hover:shadow-md',
        secondary: 'bg-surface text-text border border-border hover:bg-surface-hover active:bg-surface-active shadow-sm hover:shadow-md',
        accent: 'bg-accent text-text hover:bg-accent-600 active:bg-accent-600/90 shadow-sm hover:shadow-md',
        danger: 'bg-danger text-text hover:bg-danger/90 active:bg-danger/80 shadow-sm hover:shadow-md',
        ghost: 'text-text hover:bg-surface/50 active:bg-surface/70',
      },
      size: {
        sm: 'h-8 w-8',
        md: 'h-10 w-10',
        lg: 'h-12 w-12',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

export type IconButtonVariants = VariantProps<typeof iconButtonBase>;

/**
 * Create an input/form field variant with consistent focus and disabled states
 */
export const inputBase = cva(
  `flex items-center rounded-md border border-border bg-surface px-3 py-2 text-text placeholder:text-muted ${FOCUS_RING} ${DISABLED_STATE} ${TRANSITION}`,
  {
    variants: {
      size: {
        sm: 'h-8 text-sm',
        md: 'h-10 text-base',
        lg: 'h-12 text-lg',
      },
      state: {
        default: 'border-border hover:border-primary/50',
        error: 'border-danger focus-visible:outline-danger',
        success: 'border-success focus-visible:outline-success',
      },
    },
    defaultVariants: {
      size: 'md',
      state: 'default',
    },
  }
);

export type InputVariants = VariantProps<typeof inputBase>;

/**
 * Create a badge/label variant for small status indicators
 */
export const badgeBase = cva(
  `inline-flex items-center gap-1 font-medium rounded-sm ${TRANSITION}`,
  {
    variants: {
      variant: {
        primary: 'bg-primary/20 text-primary border border-primary/30',
        secondary: 'bg-accent/20 text-accent border border-accent/30',
        success: 'bg-success/20 text-success border border-success/30',
        warning: 'bg-warning/20 text-warning border border-warning/30',
        danger: 'bg-danger/20 text-danger border border-danger/30',
        neutral: 'bg-surface text-muted border border-border',
      },
      size: {
        sm: 'px-2 py-1 text-xs',
        md: 'px-3 py-1.5 text-sm',
        lg: 'px-4 py-2 text-base',
      },
    },
    defaultVariants: {
      variant: 'neutral',
      size: 'sm',
    },
  }
);

export type BadgeVariants = VariantProps<typeof badgeBase>;

/**
 * Create a card/surface variant
 */
export const cardBase = cva(
  `rounded-md border border-border bg-surface ${TRANSITION}`,
  {
    variants: {
      variant: {
        default: 'hover:border-primary/50 hover:shadow-md',
        interactive: `cursor-pointer hover:bg-surface-hover hover:border-primary/50 hover:shadow-md ${FOCUS_RING}`,
        elevated: 'shadow-lg hover:shadow-xl',
      },
      padding: {
        none: '',
        sm: 'p-3',
        md: 'p-4',
        lg: 'p-6',
      },
    },
    defaultVariants: {
      variant: 'default',
      padding: 'md',
    },
  }
);

export type CardVariants = VariantProps<typeof cardBase>;

/**
 * Helper: Get minimum 44x44px touch target classes
 * WCAG guideline for accessible touch targets
 */
export function getMinTouchTarget(): string {
  return 'min-h-[44px] min-w-[44px]';
}

/**
 * Helper: Merge variant props with custom classes safely
 * Ensures Tailwind doesn't conflict while allowing overrides
 */
export function mergeVariantClasses(variantClass: string, customClass?: string): string {
  if (!customClass) return variantClass;
  return `${variantClass} ${customClass}`;
}
