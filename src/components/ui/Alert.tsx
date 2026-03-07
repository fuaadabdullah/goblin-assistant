import { cva, type VariantProps } from 'class-variance-authority';
import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import IconButton from './IconButton';

const alertVariants = cva(
  'flex items-start gap-3 rounded-md border p-4 transition-all duration-150',
  {
    variants: {
      variant: {
        info: 'bg-info/10 border-info text-info',
        warning: 'bg-warning/10 border-warning text-warning',
        danger: 'bg-danger/10 border-danger text-danger',
        success: 'bg-success/10 border-success text-success',
      },
    },
    defaultVariants: {
      variant: 'info',
    },
  }
);

export type AlertVariantProps = VariantProps<typeof alertVariants>;

export interface AlertProps extends AlertVariantProps {
  title?: string;
  message: string | ReactNode;
  dismissible?: boolean;
  onDismiss?: () => void;
  icon?: ReactNode;
  className?: string;
}

const defaultIcons: Record<string, string> = {
  info: 'ℹ️',
  warning: '⚠️',
  danger: '🚨',
  success: '✓',
};

/**
 * Alert — unified alert/banner component with CVA-based variants.
 * Enforces design system colors and typography.
 */
export default function Alert({
  variant = 'info',
  title,
  message,
  dismissible = false,
  onDismiss,
  icon,
  className,
}: AlertProps) {
  const displayIcon = icon || defaultIcons[variant || 'info'];

  return (
    <div
      className={cn(alertVariants({ variant }), className)}
      role="alert"
      aria-live={variant === 'danger' ? 'assertive' : 'polite'}
    >
      <span className="flex-shrink-0 text-lg" aria-hidden="true">{displayIcon}</span>
      <div className="flex-1">
        {title && (
          <h3 className="font-semibold text-sm mb-1">{title}</h3>
        )}
        <div className="text-sm text-text">{message}</div>
      </div>
      {dismissible && onDismiss && (
        <IconButton
          variant="ghost"
          size="sm"
          icon="✕"
          aria-label="Dismiss alert"
          onClick={onDismiss}
        />
      )}
    </div>
  );
}
