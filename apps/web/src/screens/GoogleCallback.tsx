import React, { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/router';
import { queryKeys } from '../lib/query-keys';
import { persistAuthSession } from '../utils/auth-session';
import { resolvePublicBackendOrigin } from '../config/backendOrigin';
import { devError } from '@/utils/dev-log';

const GoogleCallback: React.FC = () => {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { code, state, error: oauthError } = router.query;

  useEffect(() => {
    // Wait for router to be ready
    if (!router.isReady) return;

    const handleCallback = async () => {
      const codeValue = code as string | undefined;
      const stateValue = state as string | undefined;
      const errorValue = oauthError as string | undefined;

      if (errorValue) {
        devError('OAuth error:', errorValue);
        router.push('/login?error=oauth_failed');
        return;
      }

      if (!codeValue) {
        devError('No authorization code received');
        router.push('/login?error=no_code');
        return;
      }

      try {
        const backendOrigin = resolvePublicBackendOrigin();

        // Exchange code for token
        const response = await fetch(
          `${backendOrigin}/auth/google/callback`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              code: codeValue,
              state: stateValue,
            }),
          }
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(
            `Failed to exchange code for token: ${errorData.detail || response.statusText}`
          );
        }

        const authData = await response.json();
        const tokenValue = (authData && (authData.token || authData.access_token)) || null;
        const userInfo = (authData && (authData.user || authData.userInfo)) || null;

        // Store token and user data
        if (!tokenValue || !userInfo) {
          throw new Error('Invalid OAuth response');
        }

        persistAuthSession({
          token: tokenValue,
          refreshToken: authData?.refresh_token,
          user: userInfo,
          expiresIn: authData?.expires_in,
        });
        queryClient.setQueryData(queryKeys.authValidate, {
          token: tokenValue,
          user: userInfo,
          isAuthenticated: true,
          isHydrated: true,
        });

        // Navigate to chat
        router.push('/chat');
      } catch (err) {
        devError('OAuth callback error:', err);
        router.push('/login?error=callback_failed');
      }
    };

    handleCallback();
  }, [router.isReady, code, state, oauthError, router]);

  return (
    <div className="callback-container">
      <div className="callback-content">
        <h2>Completing sign in...</h2>
        <p>Please wait while we finish signing you in with Google.</p>
        <div className="spinner"></div>
      </div>
    </div>
  );
};

// Prevent static generation - requires server-side data
export const getServerSideProps = async () => {
  return { props: {} };
};

export default GoogleCallback;
