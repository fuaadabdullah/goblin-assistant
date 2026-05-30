import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api';
import { queryKeys } from '../../lib/query-keys';
import { persistAuthSession } from '../../utils/auth-session';
import type { LoginResponse } from '../../types/api';
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
  // eslint-disable-next-line no-unused-vars
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
  const [oauthStatus, setOauthStatus] = useState<'idle' | 'captcha' | 'exchange' | 'session'>(
    'idle'
  );
  const [oauthRetryCount, setOauthRetryCount] = useState(0);
  const queryClient = useQueryClient();
  const googleAuthEnabled = featureFlags.googleAuth;

  const turnstileConfig = useTurnstile('login');

  // Retry configuration
  const MAX_OAUTH_RETRIES = 3;
  const OAUTH_TIMEOUT_MS = 30000; // 30 seconds

  // Helper: delay with exponential backoff
  const exponentialBackoff = (attempt: number): Promise<void> => {
    const delay = Math.min(1000 * Math.pow(2, attempt), 10000); // 1s, 2s, 4s, 8s, max 10s
    return new Promise((resolve) => setTimeout(resolve, delay));
  };

  // Helper: timeout wrapper for promises
  const withTimeout = <T,>(promise: Promise<T>, timeoutMs: number): Promise<T> => {
    return Promise.race([
      promise,
      new Promise<T>((_, reject) =>
        setTimeout(() => reject(new Error('Request timeout')), timeoutMs)
      ),
    ]);
  };

  useEffect(() => {
    setIsRegister(initialMode === 'register');
  }, [initialMode]);

  const handleEmailPasswordSubmit = async (email: string, password: string) => {
    setEmail(email); // Store for passkey

    // Verify Turnstile CAPTCHA completion (only when Turnstile is configured)
    if (turnstileConfig.enabled && !turnstileToken) {
      onError('Please complete the security verification');
      return;
    }

    setIsLoading(true);

    try {
      const response = isRegister
        ? await apiClient.register(email, password, turnstileToken)
        : await apiClient.login(email, password);

      const authResponse = response as LoginResponse;

      if (!authResponse.access_token) {
        throw new Error('Authentication failed - invalid server response');
      }

      persistAuthSession({
        token: authResponse.access_token,
        refreshToken: authResponse.refresh_token,
        user: authResponse.user,
        expiresIn: authResponse.expires_in,
      });
      queryClient.setQueryData(queryKeys.authValidate, {
        token: authResponse.access_token,
        user: authResponse.user,
        isAuthenticated: true,
        isHydrated: true,
      });
      onSuccess();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Authentication failed';
      const normalized =
        message.includes('timed out') || message.includes('timeout')
          ? 'Authentication service is taking too long to respond. The backend may be waking up—please try again in a few seconds.'
          : message;
      onError(normalized);
      // Reset Turnstile on error
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

    let attempt = 0;

    const tryGoogleLogin = async (): Promise<void> => {
      try {
        // Step 1: Get Google OAuth URL with timeout
        setOauthStatus('captcha');
        const response = await withTimeout(
          (async () => {
            const res = (await apiClient.getGoogleAuthUrl()) as {
              url?: string;
              authorization_url?: string;
            };
            return res;
          })(),
          OAUTH_TIMEOUT_MS
        );

        const target = response.url;
        if (!target) {
          throw new Error('Google sign-in is not configured on the server yet.');
        }

        // Step 2: Redirect to Google OAuth
        setOauthStatus('exchange');
        window.location.href = target;
      } catch (error) {
        const isTimeout = error instanceof Error && error.message.includes('timeout');
        const isNetworkError = error instanceof Error && error.message.includes('Failed to fetch');

        // Determine if we should retry
        if ((isTimeout || isNetworkError) && attempt < MAX_OAUTH_RETRIES) {
          attempt++;
          setOauthRetryCount(attempt);
          const waitMs = Math.min(1000 * Math.pow(2, attempt - 1), 10000);
          const message = isTimeout
            ? `Sign-in service not responding. Retrying in ${waitMs / 1000}s... (Attempt ${attempt}/${MAX_OAUTH_RETRIES})`
            : `Network error. Retrying in ${waitMs / 1000}s... (Attempt ${attempt}/${MAX_OAUTH_RETRIES})`;
          onError(message);
          await exponentialBackoff(attempt - 1);
          return tryGoogleLogin(); // Retry
        }

        // Final error message
        let errorMessage = 'Google sign-in failed';
        if (isTimeout) {
          errorMessage =
            'Google sign-in service is not responding. Backend may be waking up—please try again in a few seconds.';
        } else if (isNetworkError) {
          errorMessage =
            'Network error while connecting to Google. Please check your internet connection and try again.';
        } else if (error instanceof Error) {
          errorMessage = error.message || 'Failed to initiate Google sign-in';
        }

        onError(errorMessage);
        setOauthRetryCount(0);
      } finally {
        setOauthStatus('idle');
      }
    };

    setIsLoading(true);
    setOauthRetryCount(0);
    await tryGoogleLogin().finally(() => setIsLoading(false));
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

        {/* Turnstile Bot Protection (only when configured) */}
        {turnstileConfig.enabled && (
          <div className="mt-4">
            <TurnstileWidget
              siteKey={turnstileConfig.siteKey}
              onVerify={(token) => setTurnstileToken(token)}
              mode="managed"
              theme="auto"
              size="normal"
              onError={(error) => {
                devError('Turnstile verification failed:', error);
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

        {/* OAuth Progress Indicator */}
        {oauthStatus !== 'idle' && (
          <div className="mt-4 p-3 bg-primary-50 border border-primary-200 rounded-md text-center">
            <div className="text-sm text-primary font-medium">
              {oauthStatus === 'captcha' && '🔐 Verifying with Google...'}
              {oauthStatus === 'exchange' && '🔄 Completing sign-in...'}
              {oauthStatus === 'session' && '💾 Setting up session...'}
            </div>
            {oauthRetryCount > 0 && (
              <div className="text-xs text-primary-600 mt-2">
                Attempt {oauthRetryCount} of {MAX_OAUTH_RETRIES}
              </div>
            )}
          </div>
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
