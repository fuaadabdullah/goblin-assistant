import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import Spinner from '../spinner';
import { cn } from '../utils';

const buttonVariants = cva(
  'goblin-focus-ring goblin-motion-interactive goblin-pressable inline-flex items-center justify-center gap-2 rounded-md font-semibold disabled:cursor-not-allowed disabled:opacity-50',
  {
    variants: {
      variant: {
        primary:
          'bg-primary text-bg hover:bg-primary-600 active:bg-primary-600/90 shadow-md hover:shadow-lg',
        secondary:
          'bg-surface text-text border border-border hover:bg-surface-hover hover:border-primary/50 active:bg-surface-active shadow-sm hover:shadow-md',
        danger:
          'bg-danger text-bg hover:bg-danger/90 active:bg-danger/80 shadow-md hover:shadow-lg',
        success:
          'bg-success text-bg hover:bg-success/90 active:bg-success/80 shadow-md hover:shadow-lg',
        ghost:
          'bg-transparent text-text border border-border hover:bg-surface/50 active:bg-surface/70',
      },
      size: {
        sm: 'h-8 px-3 text-sm',
        md: 'h-10 px-4 text-sm',
        lg: 'h-12 px-6 text-base',
      },
      fullWidth: {
        true: 'w-full',
        false: '',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
      fullWidth: false,
    },
  }
);

export type ButtonVariantProps = VariantProps<typeof buttonVariants>;

export interface ButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'size'>, ButtonVariantProps {
  icon?: ReactNode | undefined;
  loading?: boolean | undefined;
  children: ReactNode;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      fullWidth = false,
      icon,
      loading = false,
      disabled,
      type = 'button',
      className,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size, fullWidth }), className)}
        disabled={disabled || loading}
        type={type}
        aria-busy={loading ? 'true' : undefined}
        {...props}
      >
        {loading && <Spinner aria-hidden="true" className="h-4 w-4" />}
        {!loading && icon && <span aria-hidden="true">{icon}</span>}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';

export default Button;
