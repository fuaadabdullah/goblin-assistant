import type { ReactNode } from 'react';
import PageState from './page-state';
import SectionLoadingState from './section-loading-state';
import InlineErrorState from './inline-error-state';
import EmptyState from './empty-state';

export interface TristateWrapperProps {
  children: ReactNode;
  loading?: boolean | undefined;
  error?: unknown;
  empty?: boolean | undefined;
  loadingTitle?: string | undefined;
  loadingDescription?: string | undefined;
  errorTitle?: string | undefined;
  errorMessage?: string | undefined;
  onRetry?: (() => void) | undefined;
  retryLabel?: string | undefined;
  emptyTitle?: string | undefined;
  emptyDescription?: string | undefined;
  emptyIcon?: ReactNode | undefined;
  emptyActionLabel?: string | undefined;
  onEmptyAction?: (() => void) | undefined;
  emptyActionHref?: string | undefined;
  emptySecondaryAction?: ReactNode | undefined;
  plain?: boolean | undefined;
  loadingChild?: ReactNode | undefined;
  emptyChild?: ReactNode | undefined;
  errorChild?: ReactNode | undefined;
  className?: string | undefined;
}

function resolveErrorMessage(error: unknown): string {
  if (!error) return 'An unexpected error occurred.';
  if (typeof error === 'string') return error;
  if (error instanceof Error) return error.message;
  return 'An unexpected error occurred.';
}

export default function TristateWrapper({
  children,
  loading,
  error,
  empty,
  loadingTitle = 'Loading',
  loadingDescription = 'Fetching the latest data.',
  errorTitle = 'Something went wrong',
  errorMessage,
  onRetry,
  retryLabel,
  emptyTitle = 'Nothing here yet',
  emptyDescription = 'There are no items to display.',
  emptyIcon,
  emptyActionLabel,
  onEmptyAction,
  emptyActionHref,
  emptySecondaryAction,
  plain = false,
  loadingChild,
  emptyChild,
  errorChild,
  className = '',
}: TristateWrapperProps) {
  if (loading) {
    if (loadingChild !== undefined) return <>{loadingChild}</>;
    return plain ? (
      <SectionLoadingState
        label={loadingTitle}
        description={loadingDescription}
        className={className}
      />
    ) : (
      <PageState
        variant="loading"
        title={loadingTitle}
        description={loadingDescription}
        className={className}
      />
    );
  }

  if (error) {
    if (errorChild !== undefined) return <>{errorChild}</>;
    const message = errorMessage ?? resolveErrorMessage(error);
    return plain ? (
      <InlineErrorState
        title={errorTitle}
        message={message}
        retryLabel={retryLabel}
        onRetry={onRetry}
        className={className}
      />
    ) : (
      <PageState
        variant="error"
        title={errorTitle}
        description={message}
        actionLabel={retryLabel}
        onAction={onRetry}
        className={className}
      />
    );
  }

  if (empty) {
    if (emptyChild !== undefined) return <>{emptyChild}</>;
    return plain ? (
      <EmptyState
        title={emptyTitle}
        description={emptyDescription}
        icon={emptyIcon}
        actionLabel={emptyActionLabel}
        onAction={onEmptyAction}
        actionHref={emptyActionHref}
        secondaryAction={emptySecondaryAction}
        className={className}
      />
    ) : (
      <PageState
        variant="empty"
        title={emptyTitle}
        description={emptyDescription}
        icon={emptyIcon}
        actionLabel={emptyActionLabel}
        onAction={onEmptyAction}
        actionHref={emptyActionHref}
        secondaryAction={emptySecondaryAction}
        className={className}
      />
    );
  }

  return <>{children}</>;
}
