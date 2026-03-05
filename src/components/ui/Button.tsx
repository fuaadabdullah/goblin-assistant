import type { ButtonHTMLAttributes, ReactNode } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'success' | 'ghost';
type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  icon?: ReactNode;
  loading?: boolean;
  children: ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: 'bg-primary text-text-inverse hover:bg-primary-hover shadow-glow-primary',
  secondary: 'bg-surface-hover text-text border border-border hover:bg-surface-active',
  danger: 'bg-danger text-text-inverse hover:brightness-110 shadow-[0_12px_24px_rgba(226,85,79,0.25)]',
  success: 'bg-success text-text-inverse hover:brightness-110',
  ghost: 'bg-transparent text-text border border-border hover:bg-surface-hover',
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
};

/**
 * Button — unified button component with variants and sizes.
 * Replaces duplicate button styles across the app.
 */
export default function Button({
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  icon,
  loading = false,
  disabled,
  type = 'button',
  className = '',
  children,
  ...props
}: ButtonProps) {
  const baseStyles =
    'rounded-xl font-semibold transition-all duration-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary disabled:opacity-50 disabled:cursor-not-allowed active:translate-y-[1px]';
  const widthStyles = fullWidth ? 'w-full' : '';
  const flexStyles = icon ? 'flex items-center justify-center gap-2' : '';

  return (
    <button
      className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${widthStyles} ${flexStyles} ${className}`}
      disabled={disabled || loading}
      type={type}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && <span className="animate-spin" aria-hidden="true">⟳</span>}
      {!loading && icon && <span aria-hidden="true">{icon}</span>}
      {children}
    </button>
  );
}
