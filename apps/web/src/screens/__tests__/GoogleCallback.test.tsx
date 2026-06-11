import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const mockPush = vi.fn();
let mockQuery: Record<string, string> = {};

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
  resolvePublicBackendOrigin: () => 'http://api.example.test:8000',
}));

vi.mock('@/utils/dev-log', () => ({ devError: vi.fn() }));

import GoogleCallback from '../GoogleCallback';
import { persistAuthSession } from '@/utils/auth-session';

function renderWithClient(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('GoogleCallback', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockQuery = {};
    global.fetch = vi.fn();
  });

  afterEach(() => {
    delete (global as unknown as Record<string, unknown>).fetch;
  });

  it('renders loading state', () => {
    renderWithClient(<GoogleCallback />);
    expect(screen.getByText('Completing sign in...')).toBeInTheDocument();
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

  it('exchanges code for token on success', async () => {
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
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        'http://api.example.test:8000/api/v1/auth/google/callback',
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

  it('redirects to login on fetch error', async () => {
    mockQuery = { code: 'abc123' };
    const mockFetch = global.fetch as vi.Mock;
    mockFetch.mockResolvedValue({
      ok: false,
      statusText: 'Bad Request',
      json: () => Promise.resolve({ detail: 'Invalid code' }),
    });

    renderWithClient(<GoogleCallback />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login?error=callback_failed'));
  });

  it('redirects on invalid response (no token)', async () => {
    mockQuery = { code: 'abc123' };
    const mockFetch = global.fetch as vi.Mock;
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ token: null, user: null }),
    });

    renderWithClient(<GoogleCallback />);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login?error=callback_failed'));
  });

  it('redirects on network error', async () => {
    mockQuery = { code: 'abc123' };
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
