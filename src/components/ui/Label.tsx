import * as React from 'react';
import * as LabelPrimitive from '@radix-ui/react-label';
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from '@/lib/utils';

const labelVariants = cva(
  'text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 transition-colors duration-150',
  {
    variants: {
      variant: {
        default: 'text-text-primary',
        secondary: 'text-text-secondary',
        muted: 'text-text-muted',
        required: 'text-danger after:ml-0.5 after:content-["*"]',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export type LabelVariants = VariantProps<typeof labelVariants>;

const Label = React.forwardRef<
  React.ElementRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root> & LabelVariants
>(({ className, variant, ...props }, ref) => (
  <LabelPrimitive.Root
    ref={ref}
    className={cn(labelVariants({ variant }), className)}
    {...props}
  />
));
Label.displayName = LabelPrimitive.Root.displayName;

export { Label };
