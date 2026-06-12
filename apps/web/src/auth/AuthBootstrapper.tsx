import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthSession } from '../hooks/api/useAuthSession';
import { authOnStateChange } from '../lib/supabase';
import { clearAuthSession } from '../utils/auth-session';
import { queryKeys } from '../lib/query-keys';

const AuthBootstrapper = () => {
  useAuthSession();
  const queryClient = useQueryClient();

  useEffect(() => {
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
