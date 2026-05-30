import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import ModularLoginForm from '../components/auth/ModularLoginForm';
import Seo from '../components/Seo';
import { Alert } from '../components/ui';

interface LoginPageProps {
  initialMode?: 'login' | 'register';
}

const resolveSafeRedirect = (value: string | string[] | undefined): string | null => {
  const candidate = Array.isArray(value) ? value[0] : value;
  if (typeof candidate !== 'string') return null;
  if (!candidate.startsWith('/') || candidate.startsWith('//')) return null;
  return candidate;
};

export default function LoginPage({ initialMode = 'login' }: LoginPageProps) {
  const router = useRouter();
  const { mode: paramMode, error: oauthErrorParam } = router.query;
  const [error, setError] = useState<string | null>(null);
  const [dismissedOauthMessage, setDismissedOauthMessage] = useState(false);

  const resolvedMode = useMemo(() => {
    if (paramMode === 'register') return 'register';
    return initialMode;
  }, [initialMode, paramMode]);

  const oauthError = oauthErrorParam as string | undefined;

  const oauthMessage = useMemo(() => {
    if (!oauthError) return null;
    const map: Record<string, string> = {
      oauth_failed: 'Google sign-in failed. Please try again.',
      no_code: 'Google sign-in did not return an authorization code.',
      callback_failed: 'Google sign-in could not be completed. Try again.',
    };
    return map[oauthError] || 'Authentication error. Please try again.';
  }, [oauthError]);

  useEffect(() => {
    setDismissedOauthMessage(false);
  }, [oauthError]);

  const visibleOauthMessage = dismissedOauthMessage ? null : oauthMessage;

  const handleSuccess = () => {
    setError(null);
    const redirectTo =
      resolveSafeRedirect(router.query.redirect) ?? resolveSafeRedirect(router.query.from) ?? '/';
    router.push(redirectTo);
  };

  const handleError = (message: string) => {
    setError(message);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary/10 via-accent/10 to-cta/10 px-4">
      <Seo title="Sign In" description="Sign in to Goblin Assistant." robots="noindex,nofollow" />
      <div className="w-full max-w-md">
        {(error || visibleOauthMessage) && (
          <Alert
            variant="danger"
            title="Authentication Error"
            message={error || visibleOauthMessage}
            dismissible
            onDismiss={() => {
              setError(null);
              setDismissedOauthMessage(true);
            }}
            className="mb-4"
          />
        )}

        <ModularLoginForm
          key={resolvedMode}
          initialMode={resolvedMode}
          onSuccess={handleSuccess}
          onError={handleError}
        />

        <div className="mt-6 bg-surface border border-border rounded-xl p-4 text-sm text-muted text-center">
          Want to explore first?{' '}
          <Link href="/sandbox?guest=1" className="text-primary font-medium hover:underline">
            Continue as guest
          </Link>{' '}
          to try the sandbox without saving runs.
        </div>
      </div>
    </div>
  );
}

// Prevent static generation - requires server-side data
export const getServerSideProps = async () => {
  return { props: {} };
};
