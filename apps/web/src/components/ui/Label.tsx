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
const LabelPrimitiveRoot = LabelPrimitive.Root as React.ComponentType<any>;

const Label = React.forwardRef<HTMLLabelElement, any>(({ className, variant, ...props }, ref) => (
  <LabelPrimitiveRoot ref={ref} className={cn(labelVariants({ variant }), className)} {...props} />
));
Label.displayName = LabelPrimitive.Root.displayName;

export { Label };
