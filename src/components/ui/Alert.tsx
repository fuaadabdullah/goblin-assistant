import type { ReactNode } from 'react';
import IconButton from './IconButton';

type AlertVariant = 'info' | 'warning' | 'danger' | 'success';

export interface AlertProps {
  variant?: AlertVariant;
  title?: string;
  message: string | ReactNode;
  dismissible?: boolean;
  onDismiss?: () => void;
  icon?: ReactNode;
  className?: string;
}

const variantStyles: Record<
  AlertVariant,
  { bg: string; border: string; text: string; icon: string }
> = {
  info: {
    bg: 'bg-primary/10',
    border: 'border-primary',
    text: 'text-primary',
    icon: 'ℹ️',
  },
  warning: {
    bg: 'bg-warning/10',
    border: 'border-warning',
    text: 'text-warning',
    icon: '⚠️',
  },
  danger: {
    bg: 'bg-danger/10',
    border: 'border-danger',
    text: 'text-danger',
    icon: '🚨',
  },
  success: {
    bg: 'bg-success/10',
    border: 'border-success',
    text: 'text-success',
    icon: '✓',
  },
};

/**
 * Alert — unified alert/banner component.
 * Replaces duplicate error/warning/info banners.
 */
export default function Alert({
  variant = 'info',
  title,
  message,
  dismissible = false,
  onDismiss,
  icon,
  className = '',
}: AlertProps) {
  const styles = variantStyles[variant];
  const displayIcon = icon || styles.icon;
  const ariaLive: 'assertive' | 'polite' = variant === 'danger' ? 'assertive' : 'polite';

  return (
    <div
      className={`${styles.bg} border ${styles.border} rounded-xl p-4 flex items-start gap-3 ${className}`}
      role="alert"
      aria-live={ariaLive}
    >
      <span className="text-xl flex-shrink-0">{displayIcon}</span>
      <div className="flex-1">
        {title && <h3 className={`${styles.text} font-medium text-sm mb-1`}>{title}</h3>}
        <div className="text-text text-sm">{message}</div>
      </div>
      {dismissible && onDismiss && (
        <IconButton
          variant="ghost"
          size="sm"
          icon="✕"
          aria-label="Dismiss alert"
          onClick={onDismiss}
          className={styles.text}
        />
      )}
    </div>
  );
}
