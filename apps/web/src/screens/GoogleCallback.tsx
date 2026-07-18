'use client';

import React, { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useRouter, useSearchParams } from 'next/navigation';
import { queryKeys } from '../lib/query-keys';
import { authExchangeCodeForSession } from '../lib/supabase';
import { snapshotFromSupabaseSession } from '../lib/auth-state';
import { devError } from '@/utils/dev-log';

const GoogleCallback: React.FC = () => {
  const router = useRouter();
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const code = searchParams.get('code');
  const oauthError = searchParams.get('error');

  useEffect(() => {
    const handleCallback = async () => {
      const codeValue = code ?? undefined;
      const errorValue = oauthError ?? undefined;

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
        const { session, error } = await authExchangeCodeForSession(codeValue);
        if (error || !session) {
          devError('Supabase code exchange failed:', error);
          router.push('/login?error=callback_failed');
          return;
        }
        queryClient.setQueryData(queryKeys.authValidate, snapshotFromSupabaseSession(session));
        router.push('/chat');
      } catch (err) {
        devError('OAuth callback error:', err);
        router.push('/login?error=callback_failed');
      }
    };

    handleCallback();
  }, [code, oauthError, router, queryClient]);

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

export default GoogleCallback;
