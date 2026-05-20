import { useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../lib/query-keys';
import {
  bootstrapAuthSession,
  clearAuthSessionState,
  hasAnyRole as userHasAnyRole,
  hasRole as userHasRole,
  type AuthSessionSnapshot,
} from '../../lib/auth-state';

const emptySession: AuthSessionSnapshot = {
  token: null,
  user: null,
  isAuthenticated: false,
  isHydrated: true,
};

export const useAuthSession = () => {
  const queryClient = useQueryClient();

  const authQuery = useQuery({
    queryKey: queryKeys.authValidate,
    queryFn: bootstrapAuthSession,
    retry: false,
    staleTime: 60_000,
  });

  const session = authQuery.data ?? emptySession;

  const logout = useCallback(async () => {
    await clearAuthSessionState();
    queryClient.setQueryData(queryKeys.authValidate, emptySession);
  }, [queryClient]);

  const refreshSession = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: queryKeys.authValidate });
    return authQuery.refetch();
  }, [authQuery, queryClient]);

  return {
    ...session,
    isLoading: authQuery.isLoading,
    isFetching: authQuery.isFetching,
    hasRole: (role: string) => userHasRole(session.user, role),
    hasAnyRole: (roles: string[]) => userHasAnyRole(session.user, roles),
    logout,
    refreshSession,
  };
};
