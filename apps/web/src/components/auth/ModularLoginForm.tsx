import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { authSignUp, authSignIn, authSignInWithOAuth } from '@/lib/supabase';
import { snapshotFromSupabaseSession } from '@/lib/auth-state';
import { queryKeys } from '../../lib/query-keys';
import LoginHeader from './LoginHeader';
import EmailPasswordForm from './EmailPasswordForm';
import SocialLoginButtons from './SocialLoginButtons';
import Divider from './Divider';
import PasskeyPanel from './PasskeyPanel';
import TurnstileWidget from '../TurnstileWidget';
import { useTurnstile } from '../../config/turnstile';
import { featureFlags } from '../../config/features';
import { devError } from '@/utils/dev-log';

interface ModularLoginFormProps {
  onSuccess: () => void;
  onError: (message: string) => void;
  initialMode?: 'login' | 'register';
}

export default function ModularLoginForm({
  onSuccess,
  onError,
  initialMode = 'login',
}: ModularLoginFormProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [isRegister, setIsRegister] = useState(initialMode === 'register');
  const [showPasskey, setShowPasskey] = useState(false);
  const [email, setEmail] = useState('');
  const [turnstileToken, setTurnstileToken] = useState('');
  const queryClient = useQueryClient();
  const googleAuthEnabled = featureFlags.googleAuth;
  const turnstileConfig = useTurnstile('login');

  useEffect(() => {
    setIsRegister(initialMode === 'register');
  }, [initialMode]);

  const handleEmailPasswordSubmit = async (emailValue: string, password: string) => {
    setEmail(emailValue);

    if (turnstileConfig.enabled && !turnstileToken) {
      onError('Please complete the security verification');
      return;
    }

    setIsLoading(true);
    try {
      const captchaToken = turnstileConfig.enabled ? turnstileToken : undefined;
      const { session, error } = isRegister
        ? await authSignUp(emailValue, password, captchaToken)
        : await authSignIn(emailValue, password, captchaToken);

      if (error) throw error;
      if (!session) {
        // signUp with email confirmation enabled: session is null until confirmed
        onError('Check your email to confirm your account before signing in.');
        return;
      }

      // Sets the goblin_auth/goblin_admin cookies the middleware needs —
      // without them the redirect to /chat bounces straight back to /login.
      queryClient.setQueryData(queryKeys.authValidate, snapshotFromSupabaseSession(session));
      onSuccess();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Authentication failed';
      onError(message);
      setTurnstileToken('');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    if (!googleAuthEnabled) {
      onError('Google sign-in is not enabled.');
      return;
    }

    setIsLoading(true);
    try {
      const { error } = await authSignInWithOAuth(
        'google',
        `${window.location.origin}/google-callback`
      );
      if (error) throw error;
      // Redirect happens — no further action needed here
    } catch (error) {
      devError('Google OAuth error:', error);
      onError(error instanceof Error ? error.message : 'Google sign-in failed');
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md">
      <div className="bg-surface rounded-md shadow-lg border border-border p-8 transition-all duration-150">
        <LoginHeader isRegister={isRegister} />

        <EmailPasswordForm
          onSubmit={handleEmailPasswordSubmit}
          isRegister={isRegister}
          isLoading={isLoading}
        />

        {turnstileConfig.enabled && (
          <div className="mt-4">
            <TurnstileWidget
              siteKey={turnstileConfig.siteKey}
              onVerify={(token) => setTurnstileToken(token)}
              mode="managed"
              theme="auto"
              size="normal"
              onError={(err) => {
                devError('Turnstile verification failed:', err);
                onError('Security verification failed. Please try again.');
              }}
            />
          </div>
        )}

        {googleAuthEnabled && (
          <>
            <Divider text="Or continue with" />
            <SocialLoginButtons onGoogleLogin={handleGoogleLogin} isLoading={isLoading} />
          </>
        )}

        <div className="mt-6 space-y-3">
          <button
            onClick={() => setIsRegister(!isRegister)}
            className="w-full text-center text-primary hover:text-primary-600 text-sm font-medium transition-colors"
            type="button"
          >
            {isRegister ? 'Already have an account? Sign in' : "Don't have an account? Sign up"}
          </button>

          <button
            onClick={() => setShowPasskey(!showPasskey)}
            className="w-full text-center text-accent hover:text-accent-600 text-sm font-medium transition-colors"
            type="button"
          >
            {showPasskey ? 'Hide Passkey Options' : '🔐 Use Passkey (WebAuthn)'}
          </button>
        </div>

        {showPasskey && (
          <div className="mt-6 pt-6 border-t border-divider">
            <PasskeyPanel email={email} onError={onError} onSuccess={onSuccess} />
          </div>
        )}
      </div>

      <p className="text-xs text-center text-muted mt-6">
        By signing in you agree to anonymous usage data for quality and reliability.
      </p>
    </div>
  );
}
