import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const mockPush = vi.fn();
let mockQuery: Record<string, string> = {};
const { mockAuthGetSession } = vi.hoisted(() => ({
  mockAuthGetSession: vi.fn(),
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

vi.mock('@/utils/dev-log', () => ({ devError: vi.fn(), devWarn: vi.fn(), devLog: vi.fn() }));

import * as GoogleCallbackModule from '../GoogleCallback';
vi.mock('@/lib/supabase', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/supabase')>();
  return {
    ...actual,
    authGetSession: mockAuthGetSession,
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
    mockAuthGetSession.mockResolvedValue({ session: null, error: null });
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

  it('uses the Supabase-managed session even when state is present', async () => {
    mockQuery = { code: 'abc123', state: 'xyz' };
    mockAuthGetSession.mockResolvedValueOnce({
      session: {
        access_token: 'supabase-token',
        user: { id: 'user-1' },
      },
      error: null,
    });
    const mockFetch = global.fetch as vi.Mock;

    renderWithClient(<GoogleCallback />);

    await waitFor(() => expect(mockAuthGetSession).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/chat'));
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('redirects to login when the Supabase callback has no session', async () => {
    mockQuery = { code: 'abc123', state: 'xyz' };
    const mockFetch = global.fetch as vi.Mock;

    renderWithClient(<GoogleCallback />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login?error=callback_failed'));
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('renders spinne  placeholder text', () => {
    renderWithClient(<GoogleCallback />);
    expect(screen.getByText(/Please wait/)).toBeInTheDocument();
  });
});
