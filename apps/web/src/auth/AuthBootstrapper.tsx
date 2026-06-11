import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthSession } from '../hooks/api/useAuthSession';
import { authOnStateChange } from '../lib/supabase';
import { snapshotFromSupabaseSession } from '../lib/auth-state';
import { clearAuthSession } from '../utils/auth-session';
import { queryKeys } from '../lib/query-keys';

const AuthBootstrapper = () => {
  // Trigger session bootstrap/validation through React Query.
  useAuthSession();
  const queryClient = useQueryClient();

  // Keep the query cache and middleware cookie flags in sync with Supabase:
  // SIGNED_IN / TOKEN_REFRESHED re-mirror the session, SIGNED_OUT clears it.
  useEffect(() => {
    return authOnStateChange((event, session) => {
      if (event === 'SIGNED_OUT' || !session) {
        clearAuthSession();
        queryClient.setQueryData(queryKeys.authValidate, {
          token: null,
          user: null,
          isAuthenticated: false,
          isHydrated: true,
        });
        return;
      }
      queryClient.setQueryData(queryKeys.authValidate, snapshotFromSupabaseSession(session));
    });
  }, [queryClient]);

  return null;
};

export default AuthBootstrapper;
