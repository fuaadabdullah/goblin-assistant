import { Component, ReactNode } from 'react';
import { logErrorToService, reactErrorInfoToContext } from '../utils/monitoring';
import { env } from '../config/env';
import { devError } from '@/utils/dev-log';

export interface ErrorBoundaryRenderProps {
  error: Error;
  errorId?: string;
  reset: () => void;
}

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  fallbackRender?: (props: ErrorBoundaryRenderProps) => ReactNode;
  boundaryName?: string;
  onError?: (error: Error, errorInfo: React.ErrorInfo, errorId?: string) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorId?: string;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorId: undefined };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorId: undefined };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    const context = {
      ...reactErrorInfoToContext(errorInfo),
      boundaryName: this.props.boundaryName,
    };

    let errorId: string | undefined;

    // Log to monitoring service
    if (env.isProduction) {
      errorId = logErrorToService(error, context);
    } else {
      devError('Error caught by boundary:', error, errorInfo);
    }

    this.setState({ errorId });
    this.props.onError?.(error, errorInfo, errorId);
  }

  reset = () => {
    this.setState({ hasError: false, error: null, errorId: undefined });
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallbackRender && this.state.error) {
        return this.props.fallbackRender({
          error: this.state.error,
          errorId: this.state.errorId,
          reset: this.reset,
        });
      }

      return (
        this.props.fallback || (
          <ErrorBoundaryFallback error={this.state.error!} errorId={this.state.errorId} />
        )
      );
    }

    return this.props.children;
  }
}

// Safe fallback component
export function ErrorBoundaryFallback({
  error,
  errorId,
}: {
  error: Error;
  errorId?: string;
}) {
  const isDev = env.isDevelopment;

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      <div className="max-w-md w-full bg-surface border border-border shadow-card rounded-2xl p-6">
        <div className="flex items-center justify-center w-12 h-12 mx-auto bg-danger/15 rounded-full mb-4">
          <svg
            className="w-6 h-6 text-danger"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>

        <h1 className="text-xl font-semibold text-center text-text mb-2">
          Something went wrong
        </h1>

        <p className="text-center text-muted mb-6">
          Goblin Assistant hit a render error before this page could finish loading.
        </p>

        {(isDev || errorId) && (
          <details className="mb-4 text-sm">
            <summary className="cursor-pointer text-text font-medium mb-2">Technical details</summary>
            <div className="bg-bg p-3 rounded-lg border border-border overflow-auto text-xs text-text space-y-3">
              {errorId && (
                <p>
                  Reference ID: <span className="font-mono">{errorId}</span>
                </p>
              )}
              {error && (
                <pre className="whitespace-pre-wrap break-words">
                  {isDev ? `${error.message}\n\n${error.stack || ''}`.trim() : error.message}
                </pre>
              )}
            </div>
          </details>
        )}

        <div className="flex gap-3">
          <button
            onClick={() => (window.location.href = '/')}
            className="flex-1 bg-primary text-text-inverse px-4 py-2 rounded-lg hover:brightness-110 transition shadow-glow-primary"
          >
            Go Home
          </button>
          <button
            onClick={() => window.location.reload()}
            className="flex-1 bg-surface-hover text-text px-4 py-2 rounded-lg hover:bg-surface-active transition border border-border"
          >
            Reload App
          </button>
        </div>
      </div>
    </div>
  );
}
