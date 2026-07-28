import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../utils';

const inputVariants = cva(
  'goblin-focus-ring goblin-focus-ring-inset goblin-motion-interactive flex w-full rounded-md border border-border bg-surface text-text placeholder:text-muted focus:border-primary focus:outline-none disabled:cursor-not-allowed disabled:opacity-50',
  {
    variants: {
      size: {
        sm: 'h-8 px-3 py-1 text-sm',
        md: 'h-10 px-4 py-2 text-sm',
        lg: 'h-12 px-4 py-3 text-base',
      },
      state: {
        default: 'shadow-sm focus:shadow-md',
        error: 'goblin-focus-ring-danger border-danger',
        success: 'goblin-focus-ring-success border-success',
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
  extends Omit<React.ComponentProps<'input'>, 'size'>, InputVariantProps {}

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
