import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const inputVariants = cva(
  'flex w-full rounded-md border border-border bg-surface text-text placeholder:text-muted transition-all duration-150 focus:outline-none focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-0 focus:border-primary disabled:cursor-not-allowed disabled:opacity-50',
  {
    variants: {
      size: {
        sm: 'h-8 px-3 py-1 text-sm',
        md: 'h-10 px-4 py-2 text-sm',
        lg: 'h-12 px-4 py-3 text-base',
      },
      state: {
        default: 'shadow-sm focus:shadow-md',
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

export type InputVariantProps = VariantProps<typeof inputVariants>;

export interface InputProps 
  extends Omit<React.ComponentProps<'input'>, 'size'>,
          InputVariantProps {}

/**
 * Input — form input component with CVA-based variants.
 * Enforces design system focus states and sizing.
 */
const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, size = 'md', state = 'default', ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(inputVariants({ size, state }), className)}
        ref={ref}
        {...props}
      />
    );
  }
);

Input.displayName = 'Input';

export { Input };
