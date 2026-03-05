import type { ButtonHTMLAttributes, ReactNode } from 'react';

type IconButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';
type IconButtonSize = 'sm' | 'md' | 'lg';

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: IconButtonVariant;
  size?: IconButtonSize;
  icon: ReactNode;
  'aria-label': string; // Required for accessibility
}

const variantStyles: Record<IconButtonVariant, string> = {
  primary: 'bg-primary text-text-inverse hover:bg-primary-hover shadow-glow-primary',
  secondary: 'bg-surface-hover text-text border border-border hover:bg-surface-active',
  danger: 'bg-danger text-text-inverse hover:brightness-110 shadow-[0_12px_24px_rgba(226,85,79,0.25)]',
  ghost: 'bg-transparent text-text border border-border hover:bg-surface-hover',
};

const sizeStyles: Record<IconButtonSize, string> = {
  sm: 'w-8 h-8 text-sm',
  md: 'w-10 h-10 text-base',
  lg: 'w-12 h-12 text-lg',
};

/**
 * IconButton — icon-only button with consistent sizing and variants.
 * Ensures minimum 44x44px touch target for accessibility.
 */
export default function IconButton({
  variant = 'ghost',
  size = 'md',
  icon,
  className = '',
  disabled,
  ...props
}: IconButtonProps) {
  const baseStyles =
    'rounded-xl inline-flex items-center justify-center transition-all duration-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary disabled:opacity-50 disabled:cursor-not-allowed active:translate-y-[1px]';

  return (
    <button
      className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      disabled={disabled}
      {...props}
    >
      {icon}
    </button>
  );
}
