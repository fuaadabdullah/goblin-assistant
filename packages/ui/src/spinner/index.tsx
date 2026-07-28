import { LoaderCircle } from 'lucide-react';
import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../utils';

const spinnerVariants = cva('inline-flex shrink-0 animate-spin motion-reduce:animate-none', {
  variants: {
    size: {
      sm: 'h-4 w-4',
      md: 'h-5 w-5',
      lg: 'h-6 w-6',
    },
  },
  defaultVariants: {
    size: 'md',
  },
});

export type SpinnerVariantProps = VariantProps<typeof spinnerVariants>;

export interface SpinnerProps
  extends
    Omit<React.ComponentPropsWithoutRef<typeof LoaderCircle>, 'aria-label' | 'size'>,
    SpinnerVariantProps {
  label?: string;
}

export function Spinner({ className, size = 'md', label = 'Loading', ...props }: SpinnerProps) {
  return (
    <LoaderCircle
      aria-label={label}
      role="status"
      className={cn(spinnerVariants({ size }), className)}
      {...props}
    />
  );
}

export default Spinner;
