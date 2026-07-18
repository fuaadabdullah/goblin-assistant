import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const mockPush = vi.fn();
let mockQuery: Record<string, string> = {};
const { mockAuthExchangeCodeForSession } = vi.hoisted(() => ({
  mockAuthExchangeCodeForSession: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(mockQuery),
  usePathname: () => '/google-callback',
}));

vi.mock('@/utils/auth-session', () => ({
  persistAuthSession: vi.fn(),
}));

vi.mock('@/config/backendOrigin', () => ({
  DEFAULT_BACKEND_ORIGIN: 'http://api.example.test:8000',
  resolvePublicBackendOrigin: () => 'http://api.example.test:8000',
  resolveBackendOrigin: () => 'http://api.example.test:8000',
}));

vi.mock('@/utils/dev-log', () => ({ devError: vi.fn(), devWarn: vi.fn(), devLog: vi.fn() }));

import * as GoogleCallbackModule from '../GoogleCallback';
import { persistAuthSession } from '@/utils/auth-session';

vi.mock('@/lib/supabase', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/supabase')>();
  return {
    ...actual,
    authExchangeCodeForSession: mockAuthExchangeCodeForSession,
  };
});

const GoogleCallback = GoogleCallbackModule.default;

function renderWithClient(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('GoogleCallback', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockQuery = {};
    global.fetch = vi.fn();
    mockAuthExchangeCodeForSession.mockResolvedValue({ session: null, error: new Error('no session') });
  });

  afterEach(() => {
    delete (global as unknown as Record<string, unknown>).fetch;
  });

  it('renders loading state', () => {
    renderWithClient(<GoogleCallback />);
    expect(screen.getByText('Completing sign in...')).toBeInTheDocument();
  });

  it('does not expose legacy Pages Router data hooks', () => {
    expect('getServerSideProps' in GoogleCallbackModule).toBe(false);
  });

  it('redirects on OAuth error param', async () => {
    mockQuery = { error: 'access_denied' };
    renderWithClient(<GoogleCallback />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login?error=oauth_failed'));
  });

  it('redirects when no code received', async () => {
    mockQuery = {};
    renderWithClient(<GoogleCallback />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login?error=no_code'));
  });

  it('completes the Supabase code exchange even when state is present', async () => {
    mockQuery = { code: 'abc123', state: 'xyz' };
    mockAuthExchangeCodeForSession.mockResolvedValueOnce({
      session: {
        access_token: 'supabase-token',
        user: { id: 'user-1' },
      },
      error: null,
    });
    const mockFetch = global.fetch as vi.Mock;

    renderWithClient(<GoogleCallback />);

    await waitFor(() => expect(mockAuthExchangeCodeForSession).toHaveBeenCalledWith('abc123'));
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/chat'));
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('falls back to the legacy backend callback when the Supabase exchange fails', async () => {
    mockQuery = { code: 'abc123', state: 'xyz' };
    const mockFetch = global.fetch as vi.Mock;
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          token: 'jwt-token',
          user: { id: 1, name: 'Test' },
          refresh_token: 'refresh-123',
          expires_in: 3600,
        }),
    });

    renderWithClient(<GoogleCallback />);
    await waitFor(() => expect(mockAuthExchangeCodeForSession).toHaveBeenCalledWith('abc123'));
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/auth/google/callback',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ code: 'abc123', state: 'xyz' }),
        })
      );
    });
    await waitFor(() => {
      expect(persistAuthSession).toHaveBeenCalledWith(
        expect.objectContaining({
          token: 'jwt-token',
          user: { id: 1, name: 'Test' },
        })
      );
    });
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/chat'));
  });

  it('redirects to login when the Supabase exchange fails and the backend callback errors', async () => {
    mockQuery = { code: 'abc123', state: 'xyz' };
    const mockFetch = global.fetch as vi.Mock;
    mockFetch.mockResolvedValue({
      ok: false,
      statusText: 'Bad Request',
      json: () => Promise.resolve({ detail: 'Invalid code' }),
    });

    renderWithClient(<GoogleCallback />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login?error=callback_failed'));
  });

  it('redirects to login when the Supabase exchange fails without legacy state', async () => {
    mockQuery = { code: 'abc123' };

    renderWithClient(<GoogleCallback />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login?error=callback_failed'));
  });

  it('redirects on invalid legacy backend response (no token)', async () => {
    mockQuery = { code: 'abc123', state: 'xyz' };
    const mockFetch = global.fetch as vi.Mock;
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ token: null, user: null }),
    });

    renderWithClient(<GoogleCallback />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login?error=callback_failed'));
  });

  it('redirects on legacy backend network error', async () => {
    mockQuery = { code: 'abc123', state: 'xyz' };
    const mockFetch = global.fetch as vi.Mock;
    mockFetch.mockRejectedValue(new Error('network down'));

    renderWithClient(<GoogleCallback />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login?error=callback_failed'));
  });

  it('renders spinne  placeholder text', () => {
    renderWithClient(<GoogleCallback />);
    expect(screen.getByText(/Please wait/)).toBeInTheDocument();
  });
});
