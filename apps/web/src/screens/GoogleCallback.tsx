'use client';

import React, { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useRouter, useSearchParams } from 'next/navigation';
import { queryKeys } from '../lib/query-keys';
import { authGetSession } from '../lib/supabase';
import { snapshotFromSupabaseSession } from '../lib/auth-state';
import { devError } from '@/utils/dev-log';

const GoogleCallback: React.FC = () => {
  const router = useRouter();
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const code = searchParams?.get('code');
  const oauthError = searchParams?.get('error');

  useEffect(() => {
    const handleCallback = async () => {
      const codeValue = code ?? undefined;
      const errorValue = oauthError ?? undefined;

      if (errorValue) {
        devError('OAuth error:', errorValue);
        router.push('/login?error=oauth_failed');
        return;
      }

      // createBrowserClient owns the PKCE exchange and waits for it during
      // authGetSession(). Do not exchange the code a second time or proxy it
      // through the deprecated backend OAuth flow.
      const { session, error } = await authGetSession();
      if (!error && session) {
        queryClient.setQueryData(queryKeys.authValidate, snapshotFromSupabaseSession(session));
        router.push('/chat');
        return;
      }

      if (!codeValue) {
        devError('No authorization code or Supabase session received:', error);
        router.push('/login?error=no_code');
        return;
      }

      devError('Supabase callback session unavailable:', error);
      router.push('/login?error=callback_failed');
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
