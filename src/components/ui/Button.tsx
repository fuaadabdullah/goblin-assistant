import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 font-semibold rounded-md transition-all duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2 disabled:opacity-50 disabled:cursor-not-allowed active:translate-y-[1px]',
  {
    variants: {
      variant: {
        primary: 'bg-primary text-text hover:bg-primary-600 active:bg-primary-600/90 shadow-md hover:shadow-lg',
        secondary: 'bg-surface text-text border border-border hover:bg-surface-hover hover:border-primary/50 active:bg-surface-active shadow-sm hover:shadow-md',
        danger: 'bg-danger text-text hover:bg-danger/90 active:bg-danger/80 shadow-md hover:shadow-lg',
        success: 'bg-success text-text hover:bg-success/90 active:bg-success/80 shadow-md hover:shadow-lg',
        ghost: 'bg-transparent text-text border border-border hover:bg-surface/50 active:bg-surface/70',
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
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'size'>,
          ButtonVariantProps {
  icon?: ReactNode;
  loading?: boolean;
  children: ReactNode;
}

/**
 * Button — unified button component with CVA-based variants.
 * Enforces design system: warm palette, consistent shadows, focus ring.
 */
const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({
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
  }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size, fullWidth }), className)}
        disabled={disabled || loading}
        type={type}
        aria-busy={loading ? 'true' : undefined}
        {...props}
      >
        {loading && <span className="animate-spin" aria-hidden="true">⟳</span>}
        {!loading && icon && <span aria-hidden="true">{icon}</span>}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';

export default Button;
