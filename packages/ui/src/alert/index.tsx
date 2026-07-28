import { cva, type VariantProps } from 'class-variance-authority';
import { AlertCircle, AlertTriangle, CheckCircle2, Info } from 'lucide-react';
import type { ReactNode } from 'react';
import { cn } from '../utils';
import IconButton from '../icon-button';

const alertVariants = cva('goblin-motion-colors flex items-start gap-3 rounded-md border p-4', {
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
});

export type AlertVariantProps = VariantProps<typeof alertVariants>;

export interface AlertProps extends AlertVariantProps {
  title?: string | undefined;
  message: string | ReactNode;
  dismissible?: boolean | undefined;
  onDismiss?: (() => void) | undefined;
  icon?: ReactNode | undefined;
  className?: string | undefined;
}

const defaultIcons: Record<string, ReactNode> = {
  info: <Info className="h-5 w-5" />,
  warning: <AlertTriangle className="h-5 w-5" />,
  danger: <AlertCircle className="h-5 w-5" />,
  success: <CheckCircle2 className="h-5 w-5" />,
};

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
      <span className="flex-shrink-0" aria-hidden="true">
        {displayIcon}
      </span>
      <div className="flex-1">
        {title && <h3 className="font-semibold text-sm mb-1">{title}</h3>}
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
