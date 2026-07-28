import { cva, type VariantProps } from 'class-variance-authority';
import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '../utils';

const gridVariants = cva('grid transition-all duration-150', {
  variants: {
    gap: {
      none: 'gap-0',
      xs: 'gap-1',
      sm: 'gap-2',
      md: 'gap-4',
      lg: 'gap-6',
      xl: 'gap-8',
    },
    columns: {
      auto: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4',
      1: 'grid-cols-1',
      2: 'grid-cols-1 md:grid-cols-2',
      3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
      4: 'grid-cols-2 md:grid-cols-3 lg:grid-cols-4',
    },
  },
  defaultVariants: {
    gap: 'md',
    columns: 'auto',
  },
});

export type GridVariantProps = VariantProps<typeof gridVariants>;

export interface GridProps
  extends Omit<HTMLAttributes<HTMLDivElement>, 'children'>, GridVariantProps {
  children: ReactNode;
}

export default function Grid({
  children,
  gap = 'md',
  columns = 'auto',
  className,
  ...props
}: GridProps) {
  return (
    <div className={cn(gridVariants({ gap, columns }), className)} {...props}>
      {children}
    </div>
  );
}
