import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../utils';

const iconButtonVariants = cva(
  'goblin-focus-ring goblin-motion-interactive goblin-pressable inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md disabled:cursor-not-allowed disabled:opacity-50',
  {
    variants: {
      variant: {
        primary:
          'bg-primary text-bg hover:bg-primary-600 active:bg-primary-600/90 shadow-md hover:shadow-lg',
        secondary:
          'bg-surface text-text border border-border hover:bg-surface-hover hover:border-primary/50 active:bg-surface-active shadow-sm hover:shadow-md',
        danger:
          'bg-danger text-bg hover:bg-danger/90 active:bg-danger/80 shadow-md hover:shadow-lg',
        ghost:
          'bg-transparent text-text border border-border hover:bg-surface/50 active:bg-surface/70',
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
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'size'>, IconButtonVariantProps {
  icon: ReactNode;
  'aria-label': string;
}

const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ variant = 'ghost', size = 'md', icon, className, disabled, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(iconButtonVariants({ variant, size }), className)}
        disabled={disabled}
        {...props}
      >
        <span aria-hidden="true">{icon}</span>
      </button>
    );
  }
);

IconButton.displayName = 'IconButton';

export default IconButton;
