import type { ReactNode } from 'react';
import PageState from './PageState';
import SectionLoadingState from './SectionLoadingState';
import InlineErrorState from './InlineErrorState';
import EmptyState from './EmptyState';

/**
 * A general-purpose tristate wrapper that handles loading → empty → error → content transitions.
 *
 * Three modes:
 * 1. **Page mode** – Renders full-page `PageState` (centered, full min-height).
 * 2. **Section mode** – Renders inline `SectionLoadingState` / `InlineErrorState` / `EmptyState` (no full-page layout).
 * 3. **Child mode** – You supply your own loading / empty / error elements via `loadingChild`, `emptyChild`, `errorChild`.
 *
 * By default, when `plain` is `false` (page mode), it wraps states in a full-page layout.
 * Pass `plain={true}` for section/inline rendering.
 */

/* ---------- props ---------- */

export interface TristateWrapperProps {
  /** Renders the actual content once all conditions are met. */
  children: ReactNode;

  /** Loading state – hides content when truthy. */
  loading?: boolean | undefined;
  /** Error value – when truthy shows the error state. */
  error?: unknown;
  /** Empty state – when truthy shows the empty state. */
  empty?: boolean | undefined;

  /* --- loading overrides --- */
  loadingTitle?: string | undefined;
  loadingDescription?: string | undefined;

  /* --- error overrides --- */
  errorTitle?: string | undefined;
  errorMessage?: string | undefined;
  onRetry?: (() => void) | undefined;
  retryLabel?: string | undefined;

  /* --- empty overrides --- */
  emptyTitle?: string | undefined;
  emptyDescription?: string | undefined;
  emptyIcon?: ReactNode | undefined;
  emptyActionLabel?: string | undefined;
  onEmptyAction?: (() => void) | undefined;
  emptyActionHref?: string | undefined;
  emptySecondaryAction?: ReactNode | undefined;

  /** Render in "section" (plain, non-full-page) mode instead of full-page. */
  plain?: boolean | undefined;

  /** Custom loading element – overrides all loading props when provided. */
  loadingChild?: ReactNode | undefined;
  /** Custom empty element – overrides all empty props when provided. */
  emptyChild?: ReactNode | undefined;
  /** Custom error element – overrides all error props when provided. */
  errorChild?: ReactNode | undefined;

  /** Additional className forwarded to the outermost wrapper. */
  className?: string | undefined;
}

/* ---------- helpers ---------- */

function resolveErrorMessage(error: unknown): string {
  if (!error) return 'An unexpected error occurred.';
  if (typeof error === 'string') return error;
  if (error instanceof Error) return error.message;
  return 'An unexpected error occurred.';
}

/* ---------- component ---------- */

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
  /* --- custom children take highest priority --- */
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

  /* --- normal content --- */
  return <>{children}</>;
}
