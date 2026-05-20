import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const iconButtonVariants = cva(
  'inline-flex items-center justify-center rounded-md transition-all duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2 disabled:opacity-50 disabled:cursor-not-allowed active:translate-y-[1px] min-h-[44px] min-w-[44px]',
  {
    variants: {
      variant: {
        primary: 'bg-primary text-text hover:bg-primary-600 active:bg-primary-600/90 shadow-md hover:shadow-lg',
        secondary: 'bg-surface text-text border border-border hover:bg-surface-hover hover:border-primary/50 active:bg-surface-active shadow-sm hover:shadow-md',
        danger: 'bg-danger text-text hover:bg-danger/90 active:bg-danger/80 shadow-md hover:shadow-lg',
        ghost: 'bg-transparent text-text border border-border hover:bg-surface/50 active:bg-surface/70',
      },
      size: {
        sm: 'h-8 w-8 text-sm',
        md: 'h-10 w-10 text-base',
        lg: 'h-12 w-12 text-lg',
      },
    },
    defaultVariants: {
      variant: 'ghost',
      size: 'md',
    },
  }
);

export type IconButtonVariantProps = VariantProps<typeof iconButtonVariants>;

export interface IconButtonProps 
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'size'>,
          IconButtonVariantProps {
  icon: ReactNode;
  'aria-label': string; // Required for accessibility
}

/**
 * IconButton — icon-only button with CVA-based variants.
 * Ensures minimum 44x44px touch target (WCAG compliant).
 */
const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({
    variant = 'ghost',
    size = 'md',
    icon,
    className,
    disabled,
    ...props
  }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(iconButtonVariants({ variant, size }), className)}
        disabled={disabled}
        {...props}
      >
        {icon}
      </button>
    );
  }
);

IconButton.displayName = 'IconButton';

export default IconButton;
