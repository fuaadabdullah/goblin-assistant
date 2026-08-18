import type { ReactNode } from 'react';
import Alert from './Alert';
import Button from './Button';

export interface InlineErrorStateProps {
  title?: string | undefined;
  message: string | ReactNode;
  retryLabel?: string | undefined;
  onRetry?: (() => void) | undefined;
  dismissible?: boolean | undefined;
  onDismiss?: (() => void) | undefined;
  className?: string | undefined;
}

export default function InlineErrorState({
  title = 'Something went wrong',
  message,
  retryLabel = 'Retry',
  onRetry,
  dismissible = false,
  onDismiss,
  className = '',
}: InlineErrorStateProps) {
  return (
    <Alert
      variant="danger"
      title={title}
      dismissible={dismissible}
      onDismiss={onDismiss}
      className={className}
      message={
        <div className="space-y-3">
          <div>{message}</div>
          {onRetry ? (
            <Button variant="danger" size="sm" onClick={onRetry}>
              {retryLabel}
            </Button>
          ) : null}
        </div>
      }
    />
  );
}
