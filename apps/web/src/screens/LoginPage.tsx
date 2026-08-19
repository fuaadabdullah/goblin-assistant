'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import ModularLoginForm from '../components/auth/ModularLoginForm';
import Seo from '../components/Seo';
import { Alert } from '../components/ui';

interface LoginPageProps {
  initialMode?: 'login' | 'register';
}

const resolveSafeRedirect = (value: string | string[] | null | undefined): string | null => {
  const candidate = Array.isArray(value) ? value[0] : value;
  if (typeof candidate !== 'string') return null;
  if (!candidate.startsWith('/') || candidate.startsWith('//')) return null;
  return candidate;
};

export const resolveOauthErrorMessage = (oauthError: string | null | undefined): string | null => {
  if (!oauthError) return null;

  const map: Record<string, string> = {
    oauth_failed: 'Google sign-in failed. Please try again.',
    no_code: 'Google sign-in did not return an authorization code.',
    callback_failed: 'Google sign-in could not be completed. Try again.',
    access_denied: 'Google sign-in was denied.',
    consent_required: 'Google sign-in requires consent before continuing.',
  };

  return map[oauthError] || `Authentication error: ${oauthError}`;
};

export default function LoginPage({ initialMode = 'login' }: LoginPageProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const paramMode = searchParams?.get('mode');
  const oauthErrorParam = searchParams?.get('error');
  const [error, setError] = useState<string | null>(null);
  const [dismissedOauthMessage, setDismissedOauthMessage] = useState(false);

  const resolvedMode = useMemo(() => {
    if (paramMode === 'register') return 'register';
    return initialMode;
  }, [initialMode, paramMode]);

  const oauthError = oauthErrorParam ?? undefined;

  const oauthMessage = useMemo(() => resolveOauthErrorMessage(oauthError), [oauthError]);

  useEffect(() => {
    setDismissedOauthMessage(false);
  }, [oauthError]);

  const visibleOauthMessage = dismissedOauthMessage ? null : oauthMessage;

  const handleSuccess = () => {
    setError(null);
    const redirectTo =
      resolveSafeRedirect(searchParams?.get('redirect')) ??
      resolveSafeRedirect(searchParams?.get('from')) ??
      '/';
    router.push(redirectTo);
  };

  const handleError = (message: string) => {
    setError(message);
  };

  return (
    <div className="min-h-[100dvh] overflow-x-hidden bg-[radial-gradient(circle_at_top_left,rgba(212,165,116,0.16),transparent_35%),radial-gradient(circle_at_top_right,rgba(244,150,122,0.14),transparent_32%),linear-gradient(135deg,var(--bg)_0%,#1d1712_55%,var(--bg)_100%)] px-4 py-6 sm:px-6 lg:px-8">
      <Seo title="Sign In" description="Sign in to Goblin Assistant." robots="index,follow" />
      <div className="mx-auto grid w-full max-w-6xl gap-6 lg:min-h-[calc(100dvh-3rem)] lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
        <section className="hidden overflow-hidden rounded-[28px] border border-border bg-surface/75 p-8 shadow-card backdrop-blur lg:flex lg:flex-col lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-muted">
              Goblin Assistant
            </p>
            <h1 className="mt-4 text-4xl font-semibold text-text">
              One workspace for conversations, research, and operations.
            </h1>
            <p className="mt-4 max-w-xl text-base text-muted">
              Sign in to keep your threads, pick up where you left off, and move between chat,
              search, and admin tools without losing context.
            </p>
          </div>

          <div className="mt-10 grid gap-3 sm:grid-cols-2">
            {[
              ['Guest mode', 'Try the product before creating an account.'],
              ['Saved threads', 'Keep context across devices and sessions.'],
              ['Live tools', 'Route work to chat, search, sandbox, and admin panels.'],
              ['Safer access', 'Use email, Google, or passkey sign-in.'],
            ].map(([title, body]) => (
              <div key={title} className="rounded-2xl border border-border bg-bg/70 p-4">
                <p className="text-sm font-semibold text-text">{title}</p>
                <p className="mt-1 text-sm text-muted">{body}</p>
              </div>
            ))}
          </div>
        </section>

        <div className="mx-auto w-full max-w-md">
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

          <div className="mt-6 rounded-xl border border-border bg-surface/85 p-4 text-center text-sm text-muted shadow-card backdrop-blur">
            Want to explore first?{' '}
            <Link href="/chat?guest=1" className="font-medium text-primary hover:underline">
              Continue as guest
            </Link>{' '}
            to chat without an account.
          </div>
        </div>
      </div>
    </div>
  );
}
