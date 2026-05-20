import { cva, type VariantProps } from 'class-variance-authority';
import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/utils';

const gridVariants = cva(
  'grid transition-all duration-150',
  {
    variants: {
      gap: {
        none: 'gap-0',
        xs: 'gap-1',     // 4px
        sm: 'gap-2',     // 8px
        md: 'gap-4',     // 16px
        lg: 'gap-6',     // 24px
        xl: 'gap-8',     // 32px
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
  }
);

export type GridVariantProps = VariantProps<typeof gridVariants>;

export interface GridProps 
  extends Omit<HTMLAttributes<HTMLDivElement>, 'children'>,
          GridVariantProps {
  children: ReactNode;
}

/**
 * Grid — responsive grid component with CVA-based variants.
 * Enforces design system spacing rhythm (4px base).
 */
export default function Grid({
  children,
  gap = 'md',
  columns = 'auto',
  className,
  ...props
}: GridProps) {
  return (
    <div 
      className={cn(gridVariants({ gap, columns }), className)} 
      {...props}
    >
      {children}
    </div>
  );
}
