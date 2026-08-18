import type { ReactNode } from 'react';
import Button from './Button';
import { Card, CardContent, CardHeader, CardTitle } from './card';

export interface EmptyStateProps {
  title: string;
  description: string;
  icon?: ReactNode | undefined;
  actionLabel?: string | undefined;
  onAction?: (() => void) | undefined;
  actionHref?: string | undefined;
  secondaryAction?: ReactNode | undefined;
  className?: string | undefined;
}

export default function EmptyState({
  title,
  description,
  icon,
  actionLabel,
  onAction,
  actionHref,
  secondaryAction,
  className = '',
}: EmptyStateProps) {
  const action = actionLabel ? (
    actionHref ? (
      <a
        href={actionHref}
        className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-semibold text-text transition-all hover:bg-primary-600"
      >
        {actionLabel}
      </a>
    ) : (
      <Button onClick={onAction}>{actionLabel}</Button>
    )
  ) : null;

  return (
    <Card
      className={`rounded-2xl border border-border bg-surface text-center shadow-card ${className}`}
    >
      <CardHeader className="items-center space-y-3">
        {icon ? (
          <div className="text-4xl" aria-hidden="true">
            {icon}
          </div>
        ) : null}
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="mx-auto max-w-xl text-sm text-muted">{description}</p>
        {(action || secondaryAction) && (
          <div className="flex flex-wrap items-center justify-center gap-3">
            {action}
            {secondaryAction}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
