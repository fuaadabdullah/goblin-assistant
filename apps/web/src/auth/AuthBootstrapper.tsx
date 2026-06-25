import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthSession } from '../hooks/api/useAuthSession';
import { authOnStateChange } from '../lib/supabase';
import { clearAuthSession } from '../utils/auth-session';
import { queryKeys } from '../lib/query-keys';
import { attachSupabaseInterceptor } from '../lib/api/http-client';

const AuthBootstrapper = () => {
  useAuthSession();
  const queryClient = useQueryClient();

  useEffect(() => {
    // Attach Supabase auth interceptor now that we're in a protected route.
    // This lazy-loads the Supabase module and avoids bloating public route bundles.
    attachSupabaseInterceptor().catch(() => {});

    return authOnStateChange((event) => {
      if (event === 'SIGNED_OUT') {
        clearAuthSession();
      }
      queryClient.invalidateQueries({ queryKey: queryKeys.authValidate });
    });
  }, [queryClient]);

  return null;
};

export default AuthBootstrapper;
