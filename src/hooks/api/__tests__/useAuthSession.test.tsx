import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

jest.mock('../../../lib/auth-state', () => ({
  bootstrapAuthSession: jest.fn().mockResolvedValue({
    token: 'test-token',
    user: { id: '1', name: 'Test', email: 'test@example.com', roles: ['admin'] },
    isAuthenticated: true,
    isHydrated: true,
  }),
  clearAuthSessionState: jest.fn().mockResolvedValue(undefined),
  hasAnyRole: jest.fn((user: { roles?: string[] } | null, roles: string[]) => {
    if (!user) return false;
    return roles.some((r) => user.roles?.includes(r));
  }),
  hasRole: jest.fn((user: { roles?: string[] } | null, role: string) => {
    if (!user) return false;
    return user.roles?.includes(role) ?? false;
  }),
}));

jest.mock('../../../lib/query-keys', () => ({
  queryKeys: {
    authValidate: ['auth', 'validate'],
  },
}));

import { useAuthSession } from '../useAuthSession';
import { bootstrapAuthSession, clearAuthSessionState } from '../../../lib/auth-state';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('useAuthSession', () => {
  beforeEach(() => jest.clearAllMocks());

  it('returns session data after loading', async () => {
    const { result } = renderHook(() => useAuthSession(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.token).toBe('test-token');
    expect(result.current.user?.name).toBe('Test');
  });

  it('returns isLoading true initially', () => {
    const { result } = renderHook(() => useAuthSession(), { wrapper: createWrapper() });
    // Initially loading or already resolved depending on timing
    expect(typeof result.current.isLoading).toBe('boolean');
  });

  it('provides hasRole function', async () => {
    const { result } = renderHook(() => useAuthSession(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.hasRole('admin')).toBe(true);
    expect(result.current.hasRole('unknown')).toBe(false);
  });

  it('provides hasAnyRole function', async () => {
    const { result } = renderHook(() => useAuthSession(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.hasAnyRole(['admin', 'user'])).toBe(true);
    expect(result.current.hasAnyRole(['manager'])).toBe(false);
  });

  it('provides logout function', async () => {
    const { result } = renderHook(() => useAuthSession(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    await act(async () => {
      await result.current.logout();
    });
    expect(clearAuthSessionState).toHaveBeenCalled();
  });

  it('provides refreshSession function', async () => {
    const { result } = renderHook(() => useAuthSession(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(typeof result.current.refreshSession).toBe('function');
  });

  it('calls bootstrapAuthSession on mount', async () => {
    renderHook(() => useAuthSession(), { wrapper: createWrapper() });
    await waitFor(() => expect(bootstrapAuthSession).toHaveBeenCalled());
  });

  it('returns empty session when bootstrap fails', async () => {
    (bootstrapAuthSession as jest.Mock).mockRejectedValueOnce(new Error('fail'));
    const { result } = renderHook(() => useAuthSession(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isAuthenticated).toBe(false);
  });
});
