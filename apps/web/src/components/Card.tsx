import type { PropsWithChildren, HTMLAttributes } from 'react';

export interface CardProps extends PropsWithChildren<HTMLAttributes<HTMLDivElement>> {
  elevation?: 'none' | 'card';
  padded?: boolean;
  bordered?: boolean;
  radius?: 'sm' | 'md' | 'lg';
}

/**
 * Card — primitive container that centralizes padding, radius, border, and elevation.
 * Composed by StatusCard and StatCard for consistent visuals.
 */
export default function Card({
  children,
  className = '',
  elevation = 'card',
  padded = true,
  bordered = true,
  radius = 'md',
  ...rest
}: CardProps) {
  const radiusClass =
    radius === 'lg' ? 'rounded-xl' : radius === 'sm' ? 'rounded-md' : 'rounded-lg';
  const padClass = padded ? 'p-4 md:p-5' : '';
  const borderClass = bordered ? 'border border-border' : '';
  const elevationClass = elevation === 'card' ? 'shadow-card' : '';

  return (
    <div
      className={`bg-surface ${radiusClass} ${borderClass} ${padClass} ${elevationClass} ${className}`}
      data-elevation={elevation}
      {...rest}
    >
      {children}
    </div>
  );
}
