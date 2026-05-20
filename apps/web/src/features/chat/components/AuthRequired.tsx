import Link from 'next/link';

interface AuthRequiredProps {
  className?: string;
}

/**
 * Component displayed when an unauthenticated user tries to send a message
 * Shows a friendly message with a link to sign in
 */
export const AuthRequired = ({ className = '' }: AuthRequiredProps) => {
  return (
    <div
      className={`border border-warning/20 bg-warning/5 rounded-lg p-4 ${className}`}
      role="alert"
      aria-live="polite"
    >
      <div className="flex items-start gap-3">
        <svg
          className="w-5 h-5 text-warning flex-shrink-0 mt-0.5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-warning mb-1">
            Sign in required
          </h3>
          <p className="text-sm text-text/80 mb-3">
            You need to be signed in to send messages. Create a free account or sign in to continue.
          </p>
          <div className="flex flex-wrap gap-2">
            <Link
              href="/auth/login"
              className="inline-flex items-center px-4 py-2 bg-primary text-white text-sm font-medium rounded-lg hover:bg-primary-hover transition-colors focus:outline-none focus:ring-2 focus:ring-primary/40"
            >
              Sign In
            </Link>
            <Link
              href="/auth/register"
              className="inline-flex items-center px-4 py-2 bg-surface-hover text-text text-sm font-medium rounded-lg hover:bg-surface-active transition-colors focus:outline-none focus:ring-2 focus:ring-border"
            >
              Create Account
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
