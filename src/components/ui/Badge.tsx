import { cva, type VariantProps } from 'class-variance-authority';
import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-sm font-medium transition-all duration-150',
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
        sm: 'px-2 py-0.5 text-xs',
        md: 'px-3 py-1 text-sm',
        lg: 'px-4 py-2 text-base',
      },
    },
    defaultVariants: {
      variant: 'neutral',
      size: 'sm',
    },
  }
);

export type BadgeVariantProps = VariantProps<typeof badgeVariants>;

export interface BadgeProps extends BadgeVariantProps {
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}

/**
 * Badge — status indicator component with CVA-based variants.
 * Enforces design system colors and sizing consistency.
 */
export function Badge({
  variant = 'neutral',
  size = 'sm',
  icon,
  className,
  children,
}: BadgeProps) {
  return (
    <span
      className={cn(badgeVariants({ variant, size }), className)}
      role="status"
      aria-live="polite"
    >
      {icon && <span aria-hidden="true">{icon}</span>}
      <span>{children}</span>
    </span>
  );
}

export default Badge;
