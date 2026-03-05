import type { ReactNode } from 'react';

type BadgeVariant = 'success' | 'warning' | 'danger' | 'neutral' | 'primary';
type BadgeSize = 'sm' | 'md';

export interface BadgeProps {
  variant?: BadgeVariant;
  size?: BadgeSize;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  success: 'bg-success/20 text-success',
  warning: 'bg-warning/20 text-warning',
  danger: 'bg-danger/20 text-danger',
  neutral: 'bg-surface-hover text-muted',
  primary: 'bg-primary/20 text-primary',
};

const sizeStyles: Record<BadgeSize, string> = {
  sm: 'text-xs px-2 py-0.5',
  md: 'text-sm px-3 py-1',
};

/**
 * Badge — unified status chip/badge component.
 * Replaces inline badge styles across StatusCard, health indicators, etc.
 */
export default function Badge({
  variant = 'neutral',
  size = 'sm',
  icon,
  className = '',
  children,
}: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-medium ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      role="status"
      aria-live="polite"
    >
      {icon && <span>{icon}</span>}
      <span>{children}</span>
    </span>
  );
}
