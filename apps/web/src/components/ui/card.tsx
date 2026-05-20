import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const cardVariants = cva(
  'rounded-md border border-border bg-surface text-text transition-all duration-150',
  {
    variants: {
      variant: {
        default: 'hover:border-primary/50 hover:shadow-md',
        interactive: 'cursor-pointer hover:bg-surface-hover hover:border-primary/50 hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2',
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

export type CardVariantProps = VariantProps<typeof cardVariants>;

const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement> & CardVariantProps>(
  ({ className, variant = 'default', padding = 'md', ...props }, ref) => (
    <div
      ref={ref}
      className={cn(cardVariants({ variant, padding }), className)}
      {...props}
    />
  )
);
Card.displayName = 'Card';

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex flex-col gap-1.5 p-6', className)} {...props} />
  )
);
CardHeader.displayName = 'CardHeader';

const CardTitle = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('text-xl font-semibold leading-tight tracking-tight text-text-primary', className)}
      {...props}
    />
  )
);
CardTitle.displayName = 'CardTitle';

const CardDescription = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('text-sm text-text-secondary', className)} {...props} />
  )
);
CardDescription.displayName = 'CardDescription';

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('px-6 pb-6', className)} {...props} />
  )
);
CardContent.displayName = 'CardContent';

const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex items-center gap-3 px-6 py-4 border-t border-divider', className)} {...props} />
  )
);
CardFooter.displayName = 'CardFooter';

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent };
