import Button from '../ui/Button';

interface Props {
  onJavaScriptError: () => void;
  onTypeError: () => void;
  onCustomError: () => void;
  onAsyncError: () => void;
  onNetworkError: () => void;
  onUnhandledPromiseRejection: () => void;
  onSentryError: () => void;
  onSentryMessage: () => void;
  onSentryBreadcrumb: () => void;
  onRunAll: () => void;
  running: boolean;
}

export const ErrorTestButtons = ({
  onJavaScriptError,
  onTypeError,
  onCustomError,
  onAsyncError,
  onNetworkError,
  onUnhandledPromiseRejection,
  onSentryError,
  onSentryMessage,
  onSentryBreadcrumb,
  onRunAll,
  running,
}: Props) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      <Button variant="danger" onClick={onJavaScriptError} disabled={running}>
        JavaScript Error
      </Button>
      <Button variant="danger" onClick={onTypeError} disabled={running}>
        Type Error
      </Button>
      <Button variant="danger" onClick={onCustomError} disabled={running}>
        Custom Error
      </Button>
      <Button variant="danger" onClick={onAsyncError} disabled={running}>
        Async Error
      </Button>
      <Button variant="danger" onClick={onNetworkError} disabled={running}>
        Network Error
      </Button>
      <Button variant="danger" onClick={onUnhandledPromiseRejection} disabled={running}>
        Unhandled Promise
      </Button>
      <Button variant="secondary" onClick={onSentryError} disabled={running}>
        Sentry Error
      </Button>
      <Button variant="secondary" onClick={onSentryMessage} disabled={running}>
        Sentry Message
      </Button>
      <Button variant="secondary" onClick={onSentryBreadcrumb} disabled={running}>
        Sentry Breadcrumb
      </Button>
      <Button variant="primary" onClick={onRunAll} disabled={running}>
        Run All Tests
      </Button>
    </div>
  );
};
