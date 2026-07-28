import type { ReactNode } from 'react';
import { Card, CardContent } from '../card';

export interface SectionLoadingStateProps {
  label?: string;
  description?: string;
  icon?: ReactNode;
  children?: ReactNode;
  className?: string;
}

export default function SectionLoadingState({
  label = 'Loading',
  description = 'Fetching the latest data.',
  icon,
  children,
  className = '',
}: SectionLoadingStateProps) {
  return (
    <Card
      className={`rounded-2xl border border-border bg-surface/80 shadow-card ${className}`}
      role="status"
      aria-live="polite"
      aria-label={label}
    >
      <CardContent className="flex flex-col items-center justify-center gap-4 py-10 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
          <span className="animate-pulse" aria-hidden="true">
            {icon ?? '⟳'}
          </span>
        </div>
        <div className="space-y-1">
          <p className="text-sm font-semibold text-text">{label}</p>
          <p className="text-sm text-muted">{description}</p>
        </div>
        {children}
      </CardContent>
    </Card>
  );
}
