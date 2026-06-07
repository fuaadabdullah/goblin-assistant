import type { ReactNode } from 'react';
import EmptyState from './empty-state';
import SectionLoadingState from './section-loading-state';
import InlineErrorState from './inline-error-state';

type PageStateVariant = 'loading' | 'empty' | 'error';

export interface PageStateProps {
  variant: PageStateVariant;
  title: string;
  description: string;
  icon?: ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  actionHref?: string;
  secondaryAction?: ReactNode;
  retryLabel?: string;
  className?: string;
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
