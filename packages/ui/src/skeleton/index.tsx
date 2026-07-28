import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../utils';

const skeletonVariants = cva(
  'animate-pulse rounded-md bg-surface-hover/80 motion-reduce:animate-none',
  {
    variants: {
      tone: {
        default: 'bg-surface-hover/80',
        muted: 'bg-muted/20',
        primary: 'bg-primary/15',
      },
    },
    defaultVariants: {
      tone: 'default',
    },
  }
);

export type SkeletonVariantProps = VariantProps<typeof skeletonVariants>;

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement>, SkeletonVariantProps {
  label?: string;
}

export function Skeleton({ className, tone, label = 'Loading content', ...props }: SkeletonProps) {
  return (
    <div
      aria-label={label}
      role="status"
      className={cn(skeletonVariants({ tone }), className)}
      {...props}
    />
  );
}

export default Skeleton;
