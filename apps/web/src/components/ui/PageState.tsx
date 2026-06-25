import type { ReactNode } from 'react';
import EmptyState from './EmptyState';
import SectionLoadingState from './SectionLoadingState';
import InlineErrorState from './InlineErrorState';

type PageStateVariant = 'loading' | 'empty' | 'error';

export interface PageStateProps {
  variant: PageStateVariant;
  title: string;
  description: string;
  icon?: ReactNode | undefined;
  actionLabel?: string | undefined;
  onAction?: (() => void) | undefined;
  actionHref?: string | undefined;
  secondaryAction?: ReactNode | undefined;
  retryLabel?: string | undefined;
  className?: string | undefined;
}

export default function PageState(props: PageStateProps) {
  return (
    <div className={`min-h-screen bg-bg px-4 py-12 ${props.className ?? ''}`}>
      <div className="mx-auto flex min-h-[60vh] max-w-4xl items-center justify-center">
        {props.variant === 'loading' ? (
          <SectionLoadingState
            label={props.title}
            description={props.description}
            icon={props.icon}
            className="w-full"
          />
        ) : props.variant === 'error' ? (
          <InlineErrorState
            title={props.title}
            message={props.description}
            retryLabel={props.retryLabel ?? props.actionLabel}
            onRetry={props.onAction}
            className="w-full max-w-2xl"
          />
        ) : (
          <EmptyState
            title={props.title}
            description={props.description}
            icon={props.icon}
            actionLabel={props.actionLabel}
            onAction={props.onAction}
            actionHref={props.actionHref}
            secondaryAction={props.secondaryAction}
            className="w-full max-w-2xl"
          />
        )}
      </div>
    </div>
  );
}
