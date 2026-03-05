import { Component, ReactNode } from 'react';
import { logErrorToService, reactErrorInfoToContext } from '../utils/monitoring';
import { env } from '../config/env';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log to monitoring service
    if (env.isProduction) {
      logErrorToService(error, reactErrorInfoToContext(errorInfo));
    } else {
      console.error('Error caught by boundary:', error, errorInfo);
    }
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || <ErrorBoundaryFallback error={this.state.error!} />;
    }

    return this.props.children;
  }
}

// Safe fallback component
export function ErrorBoundaryFallback({ error }: { error: Error }) {
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
          We're sorry, but the application encountered an error. Please try refreshing the page.
        </p>

        {/* ✅ Only show details in development */}
        {isDev && error && (
          <details className="mb-4 text-sm">
            <summary className="cursor-pointer text-text font-medium mb-2">
              Error Details (Development Only)
            </summary>
            <pre className="bg-bg p-3 rounded-lg border border-border overflow-auto text-xs text-text">
              {/* ✅ Safe - React escapes this automatically */}
              {error.message}
              {'\n\n'}
              {error.stack}
            </pre>
          </details>
        )}

        <div className="flex gap-3">
          <button
            onClick={() => window.location.reload()}
            className="flex-1 bg-primary text-text-inverse px-4 py-2 rounded-lg hover:brightness-110 transition shadow-glow-primary"
          >
            Refresh Page
          </button>
          <button
            onClick={() => (window.location.href = '/')}
            className="flex-1 bg-surface-hover text-text px-4 py-2 rounded-lg hover:bg-surface-active transition border border-border"
          >
            Go Home
          </button>
        </div>
      </div>
    </div>
  );
}
