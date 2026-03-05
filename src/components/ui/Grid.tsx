import type { HTMLAttributes, ReactNode } from 'react';

export interface GridProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  gap?: 'sm' | 'md' | 'lg';
  autoFit?: boolean; // Use grid-auto-fit utility
}

const gapStyles = {
  sm: 'gap-2',
  md: 'gap-4',
  lg: 'gap-6',
};

/**
 * Grid — wrapper for responsive grid layouts.
 * Uses .grid-auto-fit utility for auto-responsive card grids.
 */
export default function Grid({
  children,
  gap = 'md',
  autoFit = true,
  className = '',
  ...props
}: GridProps) {
  const gridClass = autoFit ? 'grid-auto-fit' : 'grid';

  return (
    <div className={`${gridClass} ${gapStyles[gap]} ${className}`} {...props}>
      {children}
    </div>
  );
}
