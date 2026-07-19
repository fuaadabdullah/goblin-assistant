import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const {
  mockPush,
  mockExchangeCodeForSession,
  mockSnapshotFromSupabaseSession,
  mockSetQueryData,
  queryState,
} = vi.hoisted(() => ({
  mockPush: vi.fn(),
  mockExchangeCodeForSession: vi.fn(),
  mockSnapshotFromSupabaseSession: vi.fn(() => ({
    token: 'test-token',
    user: null,
    isAuthenticated: true,
    isHydrated: true,
  })),
  mockSetQueryData: vi.fn(),
  queryState: { value: {} as Record<string, string> },
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(queryState.value),
  usePathname: () => '/google-callback',
}));

vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-query')>();
  return {
    ...actual,
    useQueryClient: () => ({ setQueryData: mockSetQueryData }),
  };
});

vi.mock('@/lib/supabase', () => ({
  authExchangeCodeForSession: mockExchangeCodeForSession,
}));

vi.mock('@/lib/auth-state', () => ({
  snapshotFromSupabaseSession: mockSnapshotFromSupabaseSession,
}));

vi.mock('@/utils/dev-log', () => ({ devError: vi.fn(), devWarn: vi.fn(), devLog: vi.fn() }));

import * as GoogleCallbackModule from '../GoogleCallback';

const GoogleCallback = GoogleCallbackModule.default;

function renderWithClient(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('GoogleCallback', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryState.value = {};
    mockExchangeCodeForSession.mockResolvedValue({
      session: {
        access_token: 'supabase-token',
        user: {
          id: 'u1',
          email: 'user@example.com',
          role: 'authenticated',
          user_metadata: { name: 'User One' },
          created_at: '2026-07-17T00:00:00Z',
        },
      },
      error: null,
    });
  });

  it('renders loading state', () => {
    renderWithClient(<GoogleCallback />);
    expect(screen.getByText('Completing sign in...')).toBeInTheDocument();
  });

  it('does not expose legacy Pages Router data hooks', () => {
    expect('getServerSideProps' in GoogleCallbackModule).toBe(false);
  });

  it('redirects on OAuth error param', async () => {
    queryState.value = { error: 'access_denied' };
    renderWithClient(<GoogleCallback />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login?error=oauth_failed'));
  });

  it('redirects when no code received', async () => {
    queryState.value = {};
    renderWithClient(<GoogleCallback />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login?error=no_code'));
  });

  it('exchanges code for session on success', async () => {
    queryState.value = { code: 'abc123', state: 'xyz' };

    renderWithClient(<GoogleCallback />);
    await waitFor(() => {
      expect(mockExchangeCodeForSession).toHaveBeenCalledWith('abc123');
    });
    await waitFor(() => {
      expect(mockSnapshotFromSupabaseSession).toHaveBeenCalledWith(
        expect.objectContaining({
          access_token: 'supabase-token',
        })
      );
    });
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/chat'));
  });

  it('redirects to login on exchange error', async () => {
    queryState.value = { code: 'abc123' };
    mockExchangeCodeForSession.mockResolvedValueOnce({
      session: null,
      error: new Error('Bad Request'),
    });

    renderWithClient(<GoogleCallback />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login?error=callback_failed'));
  });

  it('redirects on invalid response (no token)', async () => {
    queryState.value = { code: 'abc123' };
    mockExchangeCodeForSession.mockResolvedValueOnce({ session: null, error: null });

    renderWithClient(<GoogleCallback />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login?error=callback_failed'));
  });

  it('redirects on network error', async () => {
    queryState.value = { code: 'abc123' };
    mockExchangeCodeForSession.mockRejectedValueOnce(new Error('network down'));

    renderWithClient(<GoogleCallback />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login?error=callback_failed'));
  });

  it('renders spinne  placeholder text', () => {
    renderWithClient(<GoogleCallback />);
    expect(screen.getByText(/Please wait/)).toBeInTheDocument();
  });
});
